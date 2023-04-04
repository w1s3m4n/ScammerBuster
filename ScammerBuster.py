# imports
from instagrapi import Client, exceptions
import argparse
import logging
import random
import time
import re


from selenium import webdriver
from selenium.webdriver.firefox.options import Options as OptionsFirefox
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as OptionsChrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Suspicious ER. Ex: If user has 10000 followers and only 500 likes + comments: ER=> 0.05. It may be a scammer
ENGAGEMENT_RATE_THRESHOLD = 0.05

class User:
    username: str
    user_id: int
    following: []
    followers: []
    medias: []
    locations: []
    related_profiles: []
    n_followers: int
    n_following: int

    def __init__(self, username: str, user_id: int):
        self.username = username
        self.user_id = user_id
        self.followers = []
        self.following = []
        self.medias = []
        self.locations = []
        self.related_profiles = []
        self.n_followers = 0
        self.n_following = 0


    def set_following(self, following):
        self.following = following

    def set_followers(self, followers):
        self.followers = followers

    def set_medias(self, medias):
        self.medias = medias

    def set_locations(self, locations):
        self.locations = locations

    def set_related_profiles(self, related_profiles):
        self.related_profiles = related_profiles

    def set_n_followers(self, n_followers):
        self.n_followers = n_followers

    def set_n_follwing(self, n_following):
        self.n_following = n_following

    def __str__(self):
        return "{}|{}|{}|{}|{}".format(self.username, self.user_id, self.n_following, self.n_followers, self.locations)

def get_general_stats(target, cl):
    """
    Retrieve user general stats: User ID, followers list and follows list
    :param target: Username of the target
    :param cl: Instagrapi Client
    :return: user_id, following, followers
    """
    user_id = cl.user_id_from_username(target)
    time.sleep(random.randint(1, 10))

    following_structs = cl.user_following(user_id).values()
    following = [user.username for user in following_structs]

    user = User(target, user_id)
    user.set_following(following)

    # Here, we don't retrieve followers because it causes Instagram blocks. If you need it, please research how to avoid
    # it and tell me. :)

    return user


def check_potential_scammer(user):
    """
    Function that checks engagement rate and follows count to check if user can be a scammer
    :param user: User instance
    :return: True if it could be a scammer
    """

    likes = 0
    comments = 0
    for media in user.medias:
        comments += media.comment_count
        likes += media.like_count

    # If no followers, we have to suspect
    if user.n_followers == 0:
        return True

    # If low ER threshold or more following than followers, could be a scammer
    if (((likes + comments) / user.n_followers) <= ENGAGEMENT_RATE_THRESHOLD) or (user.n_followers < user.n_following):
        return True

    return False


def find_cross_followed_accounts(users, cl):
    """
    Function that checks if target accounts are follwing similar accounts (potential real relationship)
    :param users: list of User(s)
    :param cl: Instagrapi client
    :return: None
    """

    following_list = []
    for user in users:
        following_list.append(user.following)

    elements_in_all = list(set.intersection(*map(set, following_list)))

    if len(elements_in_all) > 0:
        print("[*] Found coincidences! Showing profiles...")
        for username in elements_in_all:
            print(" [!] Username: {}".format(username))
            print("     - URL: https://instagram.com/{}".format(username))
    else:
        print("[-] No coincidences found. Keep trying!")

def find_sensitive_profile_info(user: User, cl):
    """
    Function that retrieves general information about the profile and media posted
    :param user: User instance
    :param cl: Instagrapi client
    :return: The updated user instance
    """

    user_info = cl.user_info(user.user_id)

    print("[+] User account: {}".format(target))
    print(" - Followers: {}".format(user_info.follower_count))
    print(" - Following: {}".format(user_info.following_count))
    print(" - User ID: {}".format(user_info.pk))
    print(" - User Fullname: {}".format(user_info.full_name))
    print(" - User profile Pic URL: {}".format(user_info.profile_pic_url_hd))
    phones = re.findall("[\+\d]?(\d{2,3}[-\.\s]??\d{2,3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})", user_info.biography)
    mails = re.findall("[\w.+-]+@[\w-]+\.[\w.-]+", user_info.biography)
    for phone in phones:
        print(" - User potential phone: {}".format(phone))
    if user_info.contact_phone_number is not None:
        if len(user_info.contact_phone_number) > 0:
            print(" - User potential phone: {}".format(user_info.contact_phone_number))
    for mail in mails:
        print(" - User potential mail: {}".format(mail))
    if user_info.public_email is not None:
        if len(user_info.public_email) > 0:
            print(" - User potential email: {}".format(user_info.public_email))
    if user_info.external_url is not None:
        if len(user_info.external_url) > 0:
            print(" - User external URL: {}".format(user_info.external_url))
    if user_info.city_name is not None:
        if len(user_info.city_name) > 0:
            print(" - User's city: {}".format(user_info.city_name))
    if user_info.address_street is not None:
        if len(user_info.address_street) > 0:
            print(" - User's address: {}".format(user_info.address_street))

    time.sleep(random.randint(1, 10))

    # Relevant media part
    user_medias = cl.user_medias(user.user_id)

    locations = []
    related_profiles = []

    for media in user_medias:
        if media.location is not None:
            locations.append(media.location.name)
        if len(media.usertags) > 0:
            for tag in media.usertags:
                related_profiles.append(tag.user.username)

    if len(locations) > 0:
        print(" - User related locations: {}".format(', '.join(locations)))
    if len(related_profiles) > 0:
        print(" - User related profiles: {}".format(' '.join(related_profiles)))

    user.set_medias(user_medias)
    user.set_locations(locations)
    user.set_related_profiles(related_profiles)
    user.set_followers(user_info.follower_count)
    user.set_n_followers(user_info.follower_count)
    user.set_n_follwing(user_info.following_count)
    time.sleep(random.randint(1, 10))
    return user

def check_twitter_and_tiktok(user):
    """
    Function to check if a user exists in Twitter or TikTok. It may lead to false positives, but at least we can check that info.
    :param user: The User class to find
    :return: None
    """
    username = user.username

    # configure chrome options
    """
    chrome_options = OptionsChrome()
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless") # Can't find anything if using headless chrome. So using firefox.
    """

    firefox_options = OptionsFirefox()
    firefox_options.headless = True

    service = Service(executable_path="./driver/geckodriver")

    # Init Chromium
    driver = webdriver.Firefox(options=firefox_options, service=service)
    #driver = webdriver.Chrome(options=chrome_options,
    #                          executable_path="./driver/chromedriver")

    # Access to twitter
    twitter_url = "https://twitter.com/{}".format(username)
    driver.get(twitter_url)

    # We wait until the side banner with the search button appears
    wait = WebDriverWait(driver, 10)

    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[@href='/explore']")))
    except:
        pass

    # This is like killing a fly with cannons, but it works! :D
    body = driver.find_element(By.TAG_NAME, 'body')

    if username.lower() in body.text.lower():
        print(" - Found user on Twitter: {}".format(twitter_url))

    tiktok_url = "https://www.tiktok.com/@{}".format(username)
    driver.get(tiktok_url)

    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[@action='/search']")))
    except:
        pass
    # This is like killing a fly with cannons, but it works! :D
    body = driver.find_element(By.TAG_NAME, 'body')

    if username.lower() in body.text.lower():
        print(" - Found user on TikTok: {}".format(tiktok_url))

    driver.close()


def print_banner():
    print("""
    ******************************************************************************
     ____                                          ____            _            
    / ___|  ___ __ _ _ __ ___  _ __ ___   ___ _ __| __ ) _   _ ___| |_ ___ _ __ 
    \___ \ / __/ _` | '_ ` _ \| '_ ` _ \ / _ \ '__|  _ \| | | / __| __/ _ \ '__|
     ___) | (_| (_| | | | | | | | | | | |  __/ |  | |_) | |_| \__ \ ||  __/ |   
    |____/ \___\__,_|_| |_| |_|_| |_| |_|\___|_|  |____/ \__,_|___/\__\___|_|   
                    by W1s3m4n (@hackermate_)
    *******************************************************************************
    WARNING!!!: Accounts used can be blocked by Instagram. If you find lots of 
    errors, please try with another account.
       
       - The creator will not take any responsibility regarding your account -
    """)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="File from where retrieve usernames to analyze", required=True)
    parser.add_argument("-u", "--username", help="Your instagram username", required=True)
    parser.add_argument("-p", "--password", help="Your instagram password", required=True)
    parser.add_argument("-s", "--osm", help="Search for username in other social media (Twitter and TikTok)", required=False, action="store_true")
    args = parser.parse_args()

    print_banner()

    print("[*] Setting up everything and logging into Instagram...")

    logging.getLogger("instagrapi").setLevel(logging.ERROR)
    targets = open(args.file, "r").read().splitlines()

    insta_username = args.username
    insta_password = args.password

    cl = Client()

    try:
        cl.login(insta_username, insta_password)
    except exceptions.ChallengeRequired as exception:
        print("[!!!] Can't login into your account. It could be suspended. Please, access via web and double check it.")
        exit()

    users = []

    print("[*] Getting targets stats. Please wait, depends on the amount of targets, this may take a while...")

    for target in targets:
        retry = 0
        while True:
            try:
                user = get_general_stats(target, cl)
                find_sensitive_profile_info(user, cl)
            except Exception as e:
                if retry < 10:
                    waiting_time = random.randint(3, 10) * 60
                    print("[-] Error trying to fetch data for {}. Your account may be blocked. "
                          "Taking {} minutes and retrying again... ".format(target, waiting_time/60))
                    retry += 1
                    cl.logout()
                    time.sleep(waiting_time)  # Waiting between 3 and 10 minutes to retry
                    cl.login(insta_username, insta_password)
                    continue
                else:
                    # If we keep retrying up to 10 times, we exit
                    print("[-] Error trying to fetch data for {}. Your account may be blocked, "
                          "please visit Instagram normally and try again.".format(target))
                    exit(-1)
            break

        if args.osm:
            check_twitter_and_tiktok(user)

        if check_potential_scammer(user):
            print(" [!!] WARNING: Profile {} could be an scammer or have a very low engagement rate".format(target))

        users.append(user)

    if len(users) > 1:
        print("[+] Checking cross follows to try to find accounts in common")
        find_cross_followed_accounts(users, cl)
