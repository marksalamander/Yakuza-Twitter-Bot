import time
import datetime
import logging
import random
import tweepy
from os import remove
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

options = Options()
options.add_argument('-headless')
driver = webdriver.Firefox(options=options)

PLACEHOLDER_SRC = "https://static.wikia.nocookie.net/yakuza/images/4/47/Placeholder.png/revision/latest/scale-to-width-down/350?cb=20210926223337"


# Characters are posted alphabetically
def get_character():
    # Current character to be posted is read from text file.
    read_file = open("current_character.txt", "r")
    current_character = read_file.readline()
    read_file.close()

    # Names and links of each character are put into a list.
    link = []
    name = []

    # Finds all listed characters on the webpage.
    characters = driver.find_elements(By.CLASS_NAME, "category-page__member-link")

    # Iterates through the names of all the links on the webpage.
    for title in characters:
        character_name = title.get_attribute("title")
        # Skips past category links.
        if "Category" in character_name:
            continue
        # Appends the names and links of each character.
        name.append(character_name)
        link.append(title.get_attribute("href"))

    # Iterates through the list of names .
    for i in range(len(name)):
        # Finds the character to be posted within the list.
        if name[i] == current_character:

            # Goes to the character webpage by grabbing the
            # link from the list of links made prior.
            driver.get(link[i])

            # Finds the image of the character on their webpage
            image = driver.find_element(By.CLASS_NAME, "pi-image-thumbnail")
            image_name = image.get_attribute("data-image-name")

            # If the character does not have an image (has not appeared in the games)
            # the character is skipped.
            if image_name == "Placeholder.png":
                write_file = open("current_character.txt", 'w')
                write_file.write(name[i+1])
                write_file.close()
                driver.back()
                get_character()

            elif image != None:
                # The character image is saved to the character folder.
                with open(name[i] + '.png', 'wb') as file:
                    file.write(image.screenshot_as_png)

                # The current character's name in the text file
                # is replaced by the next character in the list.
                write_file = open("current_character.txt", 'w')
                write_file.write(name[i+1])
                write_file.close()

                return name[i]

            break

# A random character is chosen from the webpage
def get_random():
    page_count = 0
    next_count = random.randint(0,4)

    # Clicks the next page button 
    while page_count != next_count:
        next_button = driver.find_element(By.CLASS_NAME, 'category-page__pagination-next')
        next_button.click()
        page_count += 1
        time.sleep(1)

    # Finds all character thumbnail elements on the web page then selects a random one 
    thumbnail = driver.find_elements(By.CLASS_NAME, "category-page__member-thumbnail")
    random_link = thumbnail[random.randint(0, len(thumbnail) - 1)]
    driver.execute_script("arguments[0].click();", random_link)
    time.sleep(3)

    # If there is no image on the page, a new random character is selected
    try:
        image = driver.find_element(By.CLASS_NAME, "pi-image-thumbnail")
    except:
        get_random()
    image_src = image.get_attribute('src')

    # Gets a new random character if selected characterr does not have an image available
    if image_src == PLACEHOLDER_SRC:
        get_random()

    name = driver.find_element(By.CLASS_NAME, "page-header__title")
    name = name.text
    url = driver.current_url

    # Text to be posted on the main tweet
    text = name + '\n\n' + url
    
    # Removes quotation marks from names if applicable
    if '"' in name:
        name = name.replace('"', '')

    # Looks for the games that the character appears in
    try:
        appears_in = driver.find_elements(By.XPATH, "//div[@data-source='appears_in']//child::a")
        reply ="Appears In: \n\n"
        for games in appears_in:
            reply += (games.text + '\n')
    except:
        # If the character has no games, or the page does not have an "Appears In" tab
        # there will be no reply tweet
        reply = ""
    
    # Saves the image
    with open(name + '.png', 'wb') as file:
        file.write(image.screenshot_as_png)

    return name, text, reply

# The characters image and name is posted to the twitter account
def post(name, text, reply):
    import config

    client = tweepy.Client(config.BEARER_TOKEN, config.API_KEY, config.API_KEY_SECRET, config.ACCESS_TOKEN, config.ACCESS_TOKEN_SECRET)
    auth = tweepy.OAuth1UserHandler(config.API_KEY, config.API_KEY_SECRET, config.ACCESS_TOKEN, config.ACCESS_TOKEN_SECRET)

    api = tweepy.API(auth)

    media = api.media_upload(filename=name + '.png')
    # If the character had no game appearances, the tweet will have no reply tweet
    if reply == "":
        client.create_tweet(text=name, media_ids=[media.media_id])
    else:
        client.create_tweet(text=text, media_ids=[media.media_id])
        # Waits for the tweet to be up for a few seconds so that the reply
        # tweet does not reply to the wrong "latest" tweet
        time.sleep(10)

        # Grabs the original tweet and its tweet ID
        latestTweets = client.get_users_tweets(id=config.USER_ID)
        lastTweet = latestTweets.data[0].id
        # Replies to the tweet with the names of the games the random character
        # has appeared in
        client.create_tweet(text=reply, in_reply_to_tweet_id=lastTweet)

def main():
    driver.get("https://yakuza.fandom.com/wiki/Category:Characters")
    name, text, reply = get_random()
    driver.quit()

    post(name, text, reply)
    # Deletes the image of the character from the character folder
    remove(name + '.png')
    

main()

