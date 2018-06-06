import time
import hashlib
import datetime
import requests
import settings
import os


def check_post(submission):
    # Checks age and if not self.post
    return check_age(submission) and not check_self(submission)

def check_age(submission):
    # Checks if age is < MAX_REMEMBER_LIMIT
    return get_submission_age(submission).days < settings.MAX_REMEMBER_LIMIT

def check_self(submission):
    # Checks if is a self.post
    return submission.is_self

def get_submission_age(submission):
    # Returns a delta time object from the difference of the current time and the submission creation time
    current_date = datetime.datetime.utcfromtimestamp(time.time())
    #print submission
    submission_date = datetime.datetime.utcfromtimestamp(submission.created_utc)
    return current_date - submission_date

def initialize_link_array(reddit):
    # Initializes the link array of all past submissions
    # No need to check about removing older posts, since we do that before checking in the main loop anyway
    if not os.path.isfile("stored_posts.txt"):
        stored_posts = []
    else:
        with open("stored_posts.txt", "r") as f:
            stored_posts = f.read()
            stored_posts = stored_posts.split("\n")
            stored_posts = list(filter(None, stored_posts))
    for submission in reddit.subreddit(settings.REDDIT_SUBREDDIT).new(limit=None):
        if check_post(submission):
            if submission.url not in [sub.url for sub in stored_posts] or submission in stored_posts:
                stored_posts.append(submission)
            #list = check_list(reddit, submission, list)
    return stored_posts

def update_stored_posts(stored_posts):
    with open("stored_posts.txt", "w") as f:
        for submission in stored_posts:
            f.write(submission + "\n")

def check_list(reddit, submission, stored_posts):
    # Check if a submission url is in the list
    # If it is, remove it from the subreddit
    # If not, add it to the list
    #if check_url(submission.url) not in [check_url(sub.url) for sub in list] or submission in list:
    if submission.url not in [sub.url for sub in stored_posts] or submission in stored_posts:
        stored_posts.append(submission)
    else:
        log.info("6-month Rule: Reporting {}".format(submission.shortlink))
        # submission.mod.remove()
        reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalBot", "I DID A THING\n\nPlease look at [this post]({}) for a possible repost or check the modmail.".format(submission.shortlink))
        reddit.subreddit(settings.REDDIT_SUBREDDIT).message("ProgMetalBot - Song Repost Report", "Please look at [this post]({}) for a possible repost; if I haven't screwed up then the post is in violation of the 6-month rule.\n\nThank you!\n\n With humble gratitude, ProgMetalBot v0.1".format(submission.shortlink))
    return stored_posts

def purge_old_links(stored_posts):
    # Removes links older than settings.MAX_REMEMBER_LIMIT from the queue
    for submission in stored_posts:
        if get_submission_age(submission).days > settings.MAX_REMEMBER_LIMIT:
            stored_posts.remove(submission)
    return stored_posts

def check_url(url):
    response = requests.get(url)
    m = hashlib.md5()
    #print response.text[0:1024]
    m.update(response.text.encode("utf-8"))
    return m.digest()
