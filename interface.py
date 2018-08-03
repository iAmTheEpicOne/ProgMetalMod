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

def check_age_max(submission):
    # True if age is < MAX_REMEMBER_LIMIT
    return get_submission_age(submission).days < settings.MAX_REMEMBER_LIMIT
    
def check_age_days(submission):
    # True if age is < 48 hours
    return get_submission_age(submission).days < 2

def get_submission_age(submission):
    # Returns a delta time object from the difference of the current time and the submission creation time
    current_date = datetime.datetime.utcfromtimestamp(time.time())
    submission_date = datetime.datetime.utcfromtimestamp(submission.created_utc)
    return current_date - submission_date

def check_self(submission):
    # True if post is self.post
    return submission.is_self

def check_domain(domain):
    # Checks if link's domain is in accepted domain list
    domains = re.search('.*(youtube.com|youtu.be|spotify.com|bandcamp.com|soundcloud.com).*', domain)
    #domains = ["youtube.com", "youtu.be", "m.youtube.com", "open.spotify.com", "bandcamp.com", "soundcloud.com"]
    if domains.group(1) is not None:
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
    url = re.search('(?:youtube\.com|youtu\.be)(?:=|\/).*(.{11})', submission.url)
    if url.group(1) is not None:
        return url
    else:
        return submission.url

def get_musicbrainz_result(artist, song):
    # Checks artist and song info against musicbrainz database
    # Currently only returns True or False value
    result = musicbrainzngs.search_recordings(artist=artist, recording=song)
    # If the artist and song matches a recording in database then return True
    if not result['recording-list']:
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
    elif domain is "youtube.com" or domain is "youtu.be" or domain is "m.youtube.com":
    # Need to add YouTube API for better info
    # Currently cannot access a video's description
        link_author = submission.media.oembed.author_name
        link_media_title = submission.media.oembed.title
        if " - Topic" in link_author:
        # YouTube channel is auto-generated "Artist - Topic"
        # so video title is the song name
            song = link_media_title
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
            title = re.search('^(.*?)\s?(?:-{1,2}|\u2014|\u2013)\s?(?:"|)(\(?[^"]*?)\s?(?:["].*|(?:\(|\[|{).*[^)]$|[-([].*?(?:album|official|premiere|lyric|playthrough|single).*|$|\n)', link_media_title)
            if title is None:
                link_title = [link_media_title, None]
            else:
                artist = title.group(1).encode('utf-8')
                song = title.group(2).encode('utf-8')
                link_title = [artist, song]
    elif domain is "soundcloud.com":
    # Need to add SoundCloud API for info
        link_title = None
    else:
        link_title = None
    return link_title

def get_post_title(submission):
    # REGEX OVERLOAD INCOMING
    # Use regex string in ' ' on regexr.com and check out all the titles it catches!
    # re.search will store 'Artist' in title.group(1) and 'Song' in title.group(2)
    title = re.search('(?:(?:^[()[\]{}|].*?[()[\]{}|][\s|\W]*)|(?:^))(.*?)\s?(?:-{1,2}|\u2014|\u2013)\s?(?:"|)(\(?[^"]*?)\s?(?:\/\/.*|\\\\.*|\|\|.*|\|.*\||["].*|(?:\(|\[|{).*[^)]$|[-([|:;].*?(?:favorite|video|full|tour|premier|released|cover|album|drum|guitar|bass|vocal|voice|playthrough|ffo|official|new|metal|prog).*|$|\n)', submission.title)
    if title is None:
        #ah fuck it didn't work
        post_title = [submission.title, ""]
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

def report_musicbrainz(reddit, submission):
    # Musicbrainz query was unsuccessful
    # Submission will be reported and message sent to mods
    log.info("Song not found in Musicbrainz: Reporting {}".format(submission.shortlink))
    # ***UNCOMMENT LATER***
    #submission.report("ProgMetalBot - Not Found in Musicbrainz")
    reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalBot", "Please look at [this post]({}) for failed Musicbrainz result or check the modmail.".format(submission.shortlink))
    # ***UNCOMMENT LATER***
    #reddit.subreddit(settings.REDDIT_SUBREDDIT).message("ProgMetalBot - Bad Title Format", "Please look at [this post]({}) for failed Musicbrainz result.\n\nThank you!\n\nWith humble gratitude, ProgMetalBot".format(submission.shortlink))

def rule_bad_title(reddit, submission):
    # Submission was found to have an incorrect title
    # Submission will be reported and message sent to mods
    log.info("Rule Violation (Bad Title): Reporting {}".format(submission.shortlink))
    # ***UNCOMMENT LATER***
    #submission.report("ProgMetalBot - Bad Title Format")
    reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalBot", "Please look at [this post]({}) to check for proper title format or check the modmail.".format(submission.shortlink))
    # ***UNCOMMENT LATER***
    #reddit.subreddit(settings.REDDIT_SUBREDDIT).message("ProgMetalBot - Bad Title Format", "Please look at [this post]({}) and check for a proper title format.\n\nThank you!\n\nWith humble gratitude, ProgMetalBot".format(submission.shortlink))

def rule_bad_title_report(reddit, submission):
    # Submission was found to possibly have an incorrect title
    # Submission will only be reported to mods for verification
    log.info("Possible Rule Violation (Bad Title): Reporting {}".format(submission.shortlink))
    # ***UNCOMMENT LATER***
    #submission.report("ProgMetalBot - Possible Bad Title/Link Match")
    reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalBot", "Please look at [this post]({}) to check for proper match of submission title and linked song or check the modmail.".format(submission.shortlink))
    # ***UNCOMMENT LATER***
    #reddit.subreddit(settings.REDDIT_SUBREDDIT).message("ProgMetalBot - Bad Title Format", "Please look at [this post]({}) and check for a proper match of submission title and linked song.\n\nThank you!\n\nWith humble gratitude, ProgMetalBot".format(submission.shortlink))

def rule_six_month(reddit, submission, sub):
    # Submission was found to violate the 'repost in six months' rule
    # Submission will be reported and message sent to mods
    log.info("Rule Violation (6-month Repost): Reporting {}, repost of {}".format(submission.shortlink, sub.shortlink))
    #submission.mod.remove()
    # ***UNCOMMENT LATER***
    #submission.report("ProgMetalBot - Repost! Repost!")
    reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalBot", "Please look at [this post]({}) for a possible repost of [this post]({}) or check the modmail.".format(submission.shortlink, sub.shortlink))
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
    posts_count = 0
    for submission in reddit.subreddit(settings.REDDIT_SUBREDDIT).new(limit=None):
        if check_post(submission):
            #if submission.url not in [sub.url for sub in stored_posts] or submission not in stored_posts:
            if submission not in stored_posts and not check_age_days(submission):
                # print submission information with reports off
                #print_info(reddit, submission, 0)
                stored_posts.append(submission)
                posts_count += 1
    log.info("Found {} posts within last six months".format(posts_count))
    return stored_posts

#postgresql create table
#def create_table():
    # postgresql create table
#    commands = (
#        """
#        CREATE TABLE posts (
#            post_id SERIAL PRIMARY KEY
#        """)

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
        # link domain is not youtube, spotify, bandcamp, or soundcloud
        # could check domain against secondary list including facebook, twitter, metal magazines, etc. for different handling
        log.info("Link submission to {}".format(link_domain))
        return False
    #rules_violated = []
    post_title = submission.title
    post_info = get_post_title(submission)
    if post_info[1] is "":
        # add rule violation for bad title
        #rules_violated = rule_violation(rules_violated, 1)
        #perform_mod_actions(reddit, rules_violated)
        #rules_violated = []
        rule_bad_title(reddit, submission)
        return False
    else:
        post_artist = post_info[0]
        post_song = post_info[1]
    link_info = get_link_title(reddit, submission)
    if link_info is None:
        # None means soundcloud link which is not handled yet
        # currently: do nothing
        pass
    else:
        link_artist = link_info[0]
        link_song = link_info[1]
        if link_artist is None:
            # auto-generated YouTube channel "Various Artist - Topic"
            # artist unknown until YouTube API enabled, song is known
            if link_song is not post_song:
                # Report for link info not matching post info
                #rules_violated = rule_violation(rules_violated, 2)
                rule_bad_title_report(reddit, submission)
        elif link_song is None:
            # YouTube video title didn't match regex, so link_artist is full video title
            # Can check post_info against this info
            video_title = link_artist
            if post_artist not in video_title or post_song not in video_title:
                # Report for artist or song in post title not found in link title
                #rules_violated = rule_violation(rules_violated, 2)
                rule_bad_title_report(reddit, submission)
        elif post_artist is not link_artist or post_song is not link_song:
                # Report for artist or song in post title not found in link title
                #rules_violated = rule_violation(rules_violated, 2)
                rule_bad_title_report(reddit, submission)
    if not get_musicbrainz_result(post_artist, post_song):
        report_musicbrainz(reddit, submission)
    log.info("Domain: {:14} Song submitted: {} - {}".format(link_domain, post_artist, post_song))
    return True
    #perform_mod_actions(reddit, rules_violated)
    #rules_violated = []

def check_list(reddit, submission, stored_posts):
    # Check if a submission url is in the list:
    # If it is, report post to mods of subreddit
    # If not, add it to the list
    # Store submission in stored_posts if not already stored
    # **Unsure if redundant submissions are added to stored_posts**
    #if submission.url not in [sub.url for sub in stored_posts] or submission in stored_posts:
    
    # Check if exact url already exists
    post_url = get_url(submission)
    post_title_split = get_post_title(submission)
    post_title = post_title_split[0] + " -- " + post_title_split[1]
    for sub in stored_posts:
        #TRY TEXT MATCH AGAINST BOTH SUBMISSION TITLES/URLS
        if post_url in get_url(sub):
            rule_six_month(reddit, submission, sub)
        else:
            sub_title_split = get_post_title(sub)
            sub_title = sub_title_split[0] + " -- " + sub_title_split[1]
            if post_title in sub_title:
                rule_six_month(reddit, submission, sub)
    #log_info(submission)
    stored_posts.append(submission)
            
    #if get_url(submission) in [get_url(sub) for sub in stored_posts]:
    #    rule_six_month(reddit, submission, sub)
    # Check if title already exists
    #elif get_post_title(submission) in [get_post_title(sub) for sub in stored_posts]:
    #    rule_six_month(reddit, submission, sub)
    # print submission information with reports on
    #if submission not in stored_posts:
    #    stored_posts.append(submission)
    #print_info(reddit, submission, 1)
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

def log_info(submission):
    domain = get_domain(submission)
    title = get_post_title(submission)
    # possibly format title with .title() or capwords()
    if title[1] is "":
        title_str = title[0]
    else:
        title_str = title[0] + " - " + title[1]
    log.info("Link: {}  Domain: {:14}  Title: {}".format(submission, domain, title_str))
    
