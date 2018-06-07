import time
import hashlib
import datetime
import requests
import settings
import logging.handlers
import logging
import os


def check_post(submission):
    # True if archived and not self.post
    return check_archived(submission) and not check_self(submission)

def check_archived(submission):
    # True if post is archived (>6 months old)
    return submission.archived

def check_age(submission):
    # False if age is < MAX_REMEMBER_LIMIT
    return get_submission_age(submission).days < settings.MAX_REMEMBER_LIMIT

def check_self(submission):
    # Checks if is a self.post
    return submission.is_self

# .json "removed" value isn't available for non-removed posts
def check_removed(submission):
    # Checks if removed
    if submission.banned_by is "null":
        return false
    else:
        return true

def check_provider(submission):
    # Checks provider of link and print provider name
    domains = ["YouTube", "BandCamp", "Spotify", "SoundCloud"]
    #if submission.provider_name in domains:
    print(str(submission.provider_name))

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
            check_provider(submission)
            # **Maybe doesn't need to check url here**
            if submission.url not in [sub.url for sub in stored_posts] or submission in stored_posts:
                check_provider(submission)
                stored_posts.append(submission)
    return stored_posts

def update_stored_posts(stored_posts):
    with open("stored_posts.txt", "w") as f:
        for submission in stored_posts:
            f.write(submission + "\n")

def check_list(reddit, submission, stored_posts):
    # Check if a submission url is in the list:
    # If it is, report post to mods of subreddit
    # If not, add it to the list
    # Store submission in stored_posts if not already stored
    # **Unsure if redundent submissions are added to stored_posts**
    #if check_url(submission.url) not in [check_url(sub.url) for sub in list] or submission in list:
    check_provider(submission)
    if submission.url not in [sub.url for sub in stored_posts] or submission in stored_posts:
        check_provider(submission)
        stored_posts.append(submission)
    else:
        print("Rule Violation (6-month Repost): Reporting {}".format(submission.shortlink))
        # submission.mod.remove()
        # submission.shortlink is post in violation
        # sub.shortlink is original unreposted post
        submission.report("ProgMetalBot - Repost! Repost!")
        reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalBot", "I DID A THING\n\nPlease look at [this post]({}) for a possible repost or check the modmail.".format(submission.shortlink))
        reddit.subreddit(settings.REDDIT_SUBREDDIT).message("ProgMetalBot - Song Repost Report", "Please look at [this post]({}) for a possible repost of [this post]({}); if I haven't screwed up then the post is in violation of the 6-month rule.\n\nThank you!\n\n With humble gratitude, ProgMetalBot v0.1".format(submission.shortlink, sub.shortlink))
    return stored_posts

def purge_old_links(stored_posts):
    # Removes links archived and removed posts from queue
    for submission in stored_posts:
        if check_archived(submission) or check_removed(submission):
            stored_posts.remove(submission)
    return stored_posts

def check_url(url):
    response = requests.get(url)
    m = hashlib.md5()
    #print response.text[0:1024]
    m.update(response.text.encode("utf-8"))
    return m.digest()
