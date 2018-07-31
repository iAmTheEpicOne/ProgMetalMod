import time
import hashlib
import datetime
import requests
import settings
import logging.handlers
import logging
import os
import re
import musicbrainzngs

log = logging.getLogger("bot")
logging.getLogger("musicbrainzngs")

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

def check_domain(domain):
    # Checks if link's domain is in accepted domain list
    domains = ["youtube.com", "youtu.be", "m.youtube.com", "open.spotify.com", "bandcamp.com", "soundcloud.com"]
    if domain in domains:
        return True
    else:
        return False

def check_removed(submission):
    # .json "removed" value isn't available for non-removed posts
    # True if post is banned_by mod
    if submission.banned_by is "null":
        return False
    else:
        return True

def get_url(submission):
    # Get url
    full_url = submission.url
    if "youtube.com" in full_url:
        url = re.search('watch[?]v=.{11}', full_url)
        url = url.group(0)
        url = url[8:]
        return url
    elif "youtu.be" in full_url:
        url = re.search('\.be\/.{11}', full_url)
        url = url.group(0)
        url = url[4:]
        return url
    else:
        return submission.url

def get_musicbrainz_result(artist, song):
    # Checks artist and song info against musicbrainz database
    # Currently only returns True or False value
    result = musicbrainzngs.search_recordings(artist=artist, recording=release)
    # If the artist and song matches a recording in database then return True
    if not result['release-list']:
        return False
    return True
    
def get_domain(submission):
    return submission.domain

def get_link_title(reddit, submission):
    # Get 'Artist' and 'Song' from the embedded link info
    # Returns [artist, song] or 'None' if soundcloud link (for now)
    # Note that artist=None if auto-generated YouTube channel "Various Artist - Topic"
    # None that song=None and artist=link_title if YouTube video title didn't match regex
    #   link_title can then be used as crosscheck with reddit post title info
    domain = get_domain(submission)
    if domain is "spotify.com":
        description = submission.media.oembed.description
        title = re.search('(.*), a song by (.*) on Spotify', description)
        song = title.group(1).encode('utf-8')
        artist = title.group(2).encode('utf-8')
        link_title = [artist, song]
    elif domain is "bandcamp.com":
        description = submission.media.oembed.title
        title = re.search('(.*), by (.*)', description)
        song = title.group(1).encode('utf-8')
        artist = title.group(2).encode('utf-8')
        link_title = [artist, song]
    elif domain is "youtube.com" or domain is "youtu.be":
    # Need to add YouTube API for better info
    # Currently cannot access a video's description
        link_author = submission.media.oembed.author_name
        link_title = submission.media.oembed.title
        if " - Topic" in link_author:
        # YouTube channel is auto-generated "Artist - Topic"
        # so video title is the song name
            song = link_title
            if "Various Artists" in link_author:
            # YouTube channel is "Various Artist - Topic"
            # so artist name is unknown
            # need to use YouTube api to access video description to get correct artist name
                artist = None
            else:
                topic = re.search('(.*) - Topic', author)
                artist = topic.group(1)
            link_title = [artist, song]
        # If video is normal upload by label or user
        else:
            title = re.search('^(.*?)\s?(?:-{1,2}|\u2014|\u2013)\s?(?:"|)(\(?[^"]*?)\s?(?:["].*|(?:\(|\[|{).*[^)]$|[-([].*?(?:album|official|premiere|lyric|playthrough|single).*|$|\n)', link_title)
            if title is None:
                return [link_title, None]
            else:
                artist = title.group(1).encode('utf-8')
                song = title.group(2).encode('utf-8')
                link_title = [artist, song]
    elif domain is "soundcloud.com":
    # Need to add SoundCloud API for info
        return None
    return link_title

def get_post_title(submission):
    # REGEX OVERLOAD INCOMING
    # Use regex string in ' ' on regexr.com and check out all the titles it catches!
    # re.search will store 'Artist' in title.group(1) and 'Song' in title.group(2)
    title = re.search('(?:(?:^[()[\]{}|].*?[()[\]{}|][\s|\W]*)|(?:^))(.*?)\s?(?:-{1,2}|\u2014|\u2013)\s?(?:"|)(\(?[^"]*?)\s?(?:\/\/.*|\\\\.*|\|\|.*|\|.*\||["].*|(?:\(|\[|{).*[^)]$|[-([|:;].*?(?:favorite|video|full|tour|premier|released|cover|album|drum|guitar|bass|vocal|voice|playthrough|ffo|official|new|metal|prog).*|$|\n)', submission.title)
    if title is None:
        #ah fuck it didn't work
        return None
    else:
        artist = title.group(1).encode('utf-8')
        song = title.group(2).encode('utf-8')
        post_title = [artist, song]
        return post_title
    #title = re.search('^.+?\s(?:-{1,2}|\u2014|\u2013)\s.*$', submission.title)
    #if title is None:
    #    if reports is 1:
    #        rule_bad_title(reddit, submission)
    #    title = submission.title
    #else:
    #    title = title.group(0)
    #extra = re.search('\s[()[\]{}|].*[()[\]{}|].*$', title)
    #if not extra is None:
    #    title = title[:extra.start()] + title[extra.end():]

def rule_bad_title(reddit, submission):
    # Submission was found to have an incorrect title
    # Submission will be reported and message sent to mods
    print("Rule Violation (Bad Title): Reporting {}".format(submission.shortlink))
    # ***UNCOMMENT LATER***
    #submission.report("ProgMetalBot - Bad Title Format")
    reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalBot", "Please look at [this post]({}) to check for proper title format or check the modmail.".format(submission.shortlink))
    # ***UNCOMMENT LATER***
    #reddit.subreddit(settings.REDDIT_SUBREDDIT).message("ProgMetalBot - Bad Title Format", "Please look at [this post]({}) and check for a proper title format.\n\nThank you!\n\nWith humble gratitude, ProgMetalBot".format(submission.shortlink))

def rule_bad_title_report(reddit, submission):
    # Submission was found to possibly have an incorrect title
    # Submission will only be reported to mods for verification
    print("Possible Rule Violation (Bad Title): Reporting {}".format(submission.shortlink))
    # ***UNCOMMENT LATER***
    #submission.report("ProgMetalBot - Possible Bad Title/Link Match")
    reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalBot", "Please look at [this post]({}) to check for proper match of submission title and linked song or check the modmail.".format(submission.shortlink))
    # ***UNCOMMENT LATER***
    #reddit.subreddit(settings.REDDIT_SUBREDDIT).message("ProgMetalBot - Bad Title Format", "Please look at [this post]({}) and check for a proper match of submission title and linked song.\n\nThank you!\n\nWith humble gratitude, ProgMetalBot".format(submission.shortlink))

def rule_six_month(reddit, submission, sub):
    # Submission was found to violate the 'repost in six months' rule
    # Submission will be reported and message sent to mods
    print("Rule Violation (6-month Repost): Reporting {}".format(submission.shortlink))
    #submission.mod.remove()
    # ***UNCOMMENT LATER***
    #submission.report("ProgMetalBot - Repost! Repost!")
    reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalBot", "I DID A THING\n\nPlease look at [this post]({}) for a possible repost or check the modmail.".format(submission.shortlink))
    # ***UNCOMMENT LATER***
    #reddit.subreddit(settings.REDDIT_SUBREDDIT).message("ProgMetalBot - Song Repost Report", "Please look at [this post]({}) for a possible repost of [this post]({}); if I haven't screwed up then the post is in violation of the 6-month rule.\n\nThank you!\n\n With humble gratitude, ProgMetalBot".format(submission.shortlink, sub.shortlink))

def rule_violation(rules_violated, rule):
    # Appends a rule to rules_violated for specific submission
    rules_violated += [rule]
    return rules_violated
    
def perform_mod_actions(reddit, rules_violated):
    # For each rule in rules_violated, perform mod actions
    if len(rules_violated) > 1:
        submission = rules_violated[0]
        for rule in rules_violated[1:]:
            if rule is 1:
            # bad title
                rule_bad_title(reddit, submission)
            elif 2 in rule:
            # possible bad title - report only
                rule_bad_title_report(reddit, submission)
            elif 3 in rule:
            # six month repost
                rule_six_month(reddit, submission, rule[1])

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
                print_info(reddit, submission, 0)
                stored_posts.append(submission)
    return stored_posts

def update_stored_posts(stored_posts):
    with open("stored_posts.txt", "w") as f:
        for submission in stored_posts:
            f.write(submission + "\n")

def check_submission(reddit, submission):
    # Check the submission and link information for bad title
    # Does not check against the stored posts
    # Artist and Song name verification happens here with checks against submission title
    link_domain = get_domain(submission)
    if not check_domain(link_domain):
        # could check domain against secondary list including facebook, twitter, metal magazines, etc.
        return
    rules_violated = [submission]
    post_title = submission.title
    post_info = get_post_title(submission)
    if post_info is None:
        # add rule violation for bad title
        rules_violated = rule_violation(rules_violated, 1)
        perform_mod_actions(reddit, rules_violated)
        rules_violated = []
        return
    else:
        post_artist = post_info[0]
        post_song = post_info[1]
    link_info = get_link_title(reddit, submission)
    if link_info is None:
        # None means soundcloud link which is not handled yet
        return
    else:
        link_artist = link_info[0]
        link_song = link_info[1]
    if link_artist is None:
        # auto-generated YouTube channel "Various Artist - Topic"
        # artist unknown until YouTube API enabled, song is known
        if link_song is not post_song:
            # Report for link info not matching post info
            rules_violated = rule_violation(rules_violated, 2)
    elif link_song is None:
        # YouTube video title didn't match regex, so link_artist is full video title
        # Can check post_info against this info
        video_title = link_artist
        if post_artist not in video_title or post_song not in video_title:
            # Report for artist or song in post title not found in link title
            rules_violated = rule_violation(rules_violated, 2)
    elif post_artist is not link_artist or post_song is not link_song:
            # Report for artist or song in post title not found in link title
            rules_violated = rule_violation(rules_violated, 2)
    perform_mod_actions(reddit, rules_violated)
    rules_violated = []

def check_list(reddit, submission, stored_posts):
    # Check if a submission url is in the list:
    # If it is, report post to mods of subreddit
    # If not, add it to the list
    # Store submission in stored_posts if not already stored
    # **Unsure if redundant submissions are added to stored_posts**
    #if submission.url not in [sub.url for sub in stored_posts] or submission in stored_posts:
    
    # Check if exact url already exists
    if get_url(submission) in [get_url(sub) for sub in stored_posts]:
        rule_six_month(reddit, submission, sub)
    # Check if title already exists
    elif get_title(reddit, submission, 0) in [get_title(reddit, sub, 0) for sub in stored_posts]:
        rule_six_month(reddit, submission, sub)
    # print submission information with reports on
    if submission not in stored_posts:
        stored_posts.append(submission)
    print_info(reddit, submission, 1)
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

def print_info(reddit, submission, reports):
    domain = get_domain(submission)
    title = get_title(reddit, submission, reports)
    # possibly format title with .title() or capwords()
    print("Link: {}  Domain: {:14}  Title: {}".format(submission, domain, title))
    
