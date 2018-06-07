import time
import hashlib
import datetime
import requests
import settings
import logging.handlers
import logging
import os
import re


def check_post(submission):
    # True if not archived and not self.post
    return not check_archived(submission) and not check_self(submission)

def check_archived(submission):
    # True if post is archived (>6 months old)
    return submission.archived

def check_age(submission):
    # True if age is < MAX_REMEMBER_LIMIT
    return get_submission_age(submission).days < settings.MAX_REMEMBER_LIMIT

def get_submission_age(submission):
    # Returns a delta time object from the difference of the current time and the submission creation time
    current_date = datetime.datetime.utcfromtimestamp(time.time())
    #print submission
    submission_date = datetime.datetime.utcfromtimestamp(submission.created_utc)
    return current_date - submission_date

def check_self(submission):
    # True if post is self.post
    return submission.is_self

# .json "removed" value isn't available for non-removed posts
def check_removed(submission):
    # True if post is banned_by mod
    if submission.banned_by is "null":
        return False
    else:
        return True

def get_domain(submission):
    # Checks domain of link and print submission and domain name
    # Returns domain name
    # domains = ["youtube.com", "youtu.be", "open.spotify.com", "bandcamp.com", "soundcloud.com"]
    name = re.search('(spotify.com|bandcamp.com|soundcloud.com|youtube.com|youtu.be)', submission.domain)
    if not name is None:
        return name.group(0)
    else:
        return submission.domain

def get_title(submission, reports):
    domain = get_domain(submission)
    if domain is "spotify.com":
        description = submission.media.oembed.description
        song, band = description.split(", a song by ", 1)
        extra = re.search(' on Spotify', band)
        band = band[:extra.start()]
        if song not in submission.title or band not in submission.title:
            # song or band is not in submission title
            #   so title has bad format
            if reports is 1:
                rule_bad_title(reddit, submission)
        title = band + " - " + song
    elif domain is "bandcamp.com":
        description = submission.media.oembed.title
        song, band = description.split(", by ", 1)
        if song not in submission.title or band not in submission.title:
            # song or band is not in submission title
            #   so title has bad format
            if reports is 1:
                rule_bad_title(reddit, submission)
        title = band + " - " + song
    else:
        title = re.search('^.+?\s(?:-{1:2}|\u2014|\u2013).*$', submission.title)
        if title is None:
            if reports is 1:
                rule_bad_title(reddit, submission)
            title = submission.title
        extra = re.search('\s(\(|\[|\|).*(\)|\]|\|)', title)
        if not extra is None:
            title = title[:extra.start()] + title[extra.end():]
    return title.encode('utf-8')
'''
getting proper title of youtube and soundcloud links is going to be difficult
    elif domain is "soundcloud.com:
        
    elif domain is "youtube.com" or domain is "youtu.be":
        #description = submission.title
        #remove = re.search('\(.*\)', description)
        #description.
        author = submission.media.oembed.author_name

        if " - Topic" in author:
            if "Various Artists" in author:
                # YouTube channel is "Various Artists - Topic"
                #   so song name is media.oembed.title
                song = submission.media.oembed.title
                description = submission.title
                if song not in description:
                    # song is not in the submission title
                    #   so title has bad format
                    if reports is 1:
                        rule_bad_title(reddit, submission)
                extra = re.search('(\(|\[).*?(\)|\])', description)
                description = description[:extra.start()] + description[extra.end():]
            topic = re.search(" - Topic", author)
            author = author[:topic.start()]
        description = submission.media.oembed.title
        
        elif author in submission.title:


'''

    

def rule_six_month(reddit, submission, sub):
    print("Rule Violation (6-month Repost): Reporting {}".format(submission.shortlink))
    # submission.mod.remove()
    # submission is post in violation
    # sub is original unreposted post
    submission.report("ProgMetalBot - Repost! Repost!")
    reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalBot", "I DID A THING\n\nPlease look at [this post]({}) for a possible repost or check the modmail.".format(submission.shortlink))
    reddit.subreddit(settings.REDDIT_SUBREDDIT).message("ProgMetalBot - Song Repost Report", "Please look at [this post]({}) for a possible repost of [this post]({}); if I haven't screwed up then the post is in violation of the 6-month rule.\n\nThank you!\n\n With humble gratitude, ProgMetalBot v0.1".format(submission.shortlink, sub.shortlink))

def rule_bad_title(reddit, submission):
    print("Rule Violation (Bad Title): Reporting {}".format(submission.shortlink))
    # Submission was found to have an incorrect title
    submission.report("ProgMetalBot - Bad Title Format")
    reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalBot", "Please look at [this post]({}) to check for proper title format or check the modmail.".format(submission.shortlink))
    reddit.subreddit(settings.REDDIT_SUBREDDIT).message("ProgMetalBot - Bad Title Format", "Please look at [this post]({}) and check for a proper title format.\n\nThank you!\n\nWith humble gratitude, ProgMetalBot v0.1".format(submission.shortlink))

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
            if submission.url not in [sub.url for sub in stored_posts] or submission not in stored_posts:
                # print submission information with reports off
                print_info(submission, 0)
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
    #if submission.url not in [sub.url for sub in stored_posts] or submission in stored_posts:
    
    if submission not in stored_posts:
        stored_posts.append(submission)
    # Check if exact url already exists
    if submission.url in [sub.url for sub in stored_posts]:
        rule_six_month(reddit, submission, sub)
    # Check if title already exists
    elif get_title(submission, 0) in [get_title(sub, 0) for sub in stored_posts]:
        rule_six_month(reddit, submission, sub)
    # print submission information with reports on
    print_info(submission, 1)
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

def print_info(submission, reports):
    domain = get_domain(submission)
    title = get_title(submission, reports)
    # possibly format title with .title() or capwords()
    print("Link: {}  Domain: {:14}  Title: {}".format(submission, domain, title))
    
