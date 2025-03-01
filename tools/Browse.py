import random, os, time, sys
from get_project_root import root_path
import pandas as pd
from datetime import datetime
import shutil
import tempfile
import re
import string
from typing import Any, Generator
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from bs4 import BeautifulSoup
from urllib.parse import parse_qs, unquote, urlparse, urlunparse
import pytz, humanfriendly

ROOT_DIR = root_path(ignore_cwd=False)

TEMP_SESSION_PREFIX = 'fb_page_session'

def generate_chrome_driver() -> tuple[WebDriver, str]:
    """A tool that generates chrome web driver in order to drive the browser and open a link
    Returns:
        Instance that controls the Chrome webDriver and allows you to drive the browser
    """
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    temp_folder = os.path.join(
            tempfile.gettempdir(), f"{TEMP_SESSION_PREFIX}{random_string}"
        )

    # Create the random temp folder
    os.makedirs(temp_folder, exist_ok=True)
    source_dir = rf"/root/.config/google-chrome"
    if os.path.exists(source_dir):
        shutil.copytree(source_dir, temp_folder, dirs_exist_ok=True)
    # else:
    #     raise Exception(
    #         f'Error: Source directory not found. You have to run "python login.py docker" first, at least once.'
    #     )
    # for singleton in ["SingletonCookie", "SingletonLock", "SingletonSocket"]:
    #         if os.path.islink(f"{temp_folder}/{singleton}"):
    #             os.unlink(f"{temp_folder}/{singleton}")
    
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument(f"--user-data-dir={temp_folder}")
    
    return webdriver.Chrome(options=chrome_options), temp_folder


def wait(d: int) -> None:
    """A tool for waiting. it replaces the time.sleep()
    Args:
        d: an integer that sets how many seconds it should wait
    """
    time.sleep(d)
def tree_keyword_lookup(search_term: str, post: WebElement):
    matching_strings = [] 
    soup = BeautifulSoup(post.get_attribute('outerHTML'), 'html.parser') 
    
    # Loop through all elements within the HTML content
    for element in soup.find_all(True):  # True to find all elements
        # Check if search_term is in the element's text (substring match)
        text = element.get_text()
        if search_term in text:  # Check if search_term is part of the text
            matching_strings.append(text.strip())  # Add text if it contains the search_term

        # Check each attribute for search_term (substring match)
        for attribute, value in element.attrs.items(): 
            # Handle cases where the attribute value is a list (e.g., class)
            if isinstance(value, list):
                for v in value:
                    if search_term in v:  # Check if search_term is part of the attribute value
                        matching_strings.append(v.strip())  # Add the matched attribute value
                        break
            else:
                if search_term in value:  # Check if search_term is part of the attribute value
                    matching_strings.append(value.strip())  # Add the matched attribute value

    return matching_strings

def scrollbottom(driver: WebDriver):
    driver.execute_script("window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });")
    wait(2)
def scrolltarget(driver: WebDriver, element: WebElement):
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
    wait(2)
def scrolltop(driver:WebDriver):
    driver.execute_script("window.scrollTo({ top: 0, behavior: 'smooth' });")
    wait(2)
def is_page_loaded(driver: WebDriver) -> bool:
    """ A tool that checks whether the page is fully loaded or not. if it's fully loaded, it'll return True, otherwise False.
    Args:
        driver: an instance that controls the chrome webdriver and allows you to drive the browser
    Return:
        Bool whether the driver fully loaded the page or not.
    """
    return driver.execute_script("return document.readyState") == "complete"

def get_facebook_post_from_whatsapp_share(url):
    # Parse the URL to extract query parameters
    parsed_url = urlparse(url)
    
    # Extract the 'u' parameter, which contains the WhatsApp URL with the 'text' parameter
    query_params = parse_qs(parsed_url.query)
    whatsapp_url = query_params.get('u', [None])[0]
    
    if whatsapp_url:
        # Decode the WhatsApp URL
        decoded_whatsapp_url = unquote(whatsapp_url)
        
        # Extract the 'text' parameter from the decoded WhatsApp URL
        whatsapp_parsed_url = urlparse(decoded_whatsapp_url)
        whatsapp_query_params = parse_qs(whatsapp_parsed_url.query)
        post_url = whatsapp_query_params.get('text', [None])[0]
        
        if post_url:
            # Decode the final Facebook post URL
            decoded_post_url = unquote(post_url)
            return decoded_post_url
        
    return None
def get_facebook_post_from_embed(embed_code: str) -> str:
    """
    Extracts the Facebook post URL from an embedded post code string.

    This function takes an embedded Facebook post code string, parses it, 
    and extracts the URL of the post embedded in the code.

    Args:
        embed_code: The embedded code string of a Facebook post from which the post URL is to be extracted.

    Returns:
        str: The URL of the Facebook post embedded in the provided code string.

    Note:
    - The function assumes that the embedded code string is in the expected 
      format for a Facebook post embed.
    - The function will return an None or raise an error if the embedded code 
      does not contain a valid Facebook post URL.
    """
    # Parse the iframe embed code using BeautifulSoup
    soup = BeautifulSoup(embed_code, 'html.parser')
    
    # Find the iframe tag and extract the src attribute
    iframe = soup.find('iframe')
    
    if iframe and 'src' in iframe.attrs:
        # Get the URL from the src attribute
        encoded_url = iframe.attrs['src']
        
        # Extract the actual Facebook post URL from the href parameter
        match = re.search(r'href=([^&]+)', encoded_url)
        
        if match:
            # Decode the URL to get the original post URL
            decoded_url = unquote(match.group(1))
            return decoded_url
    
    return embed_code
def trycatch(c):
    try: return c()
    except: return None

def close_dialog(driver:WebDriver, action: ActionChains, dialog: WebElement):
    close = dialog.find_element(By.XPATH, './/*[@role="button" and @aria-label="Close"]')
    while True:
        action.move_to_element(close).click().perform()
        try:
            WebDriverWait(driver, 1, 1).until(EC.invisibility_of_element_located(dialog))
            break
        except:
            print('cant find dialog close button')

def embed_technique(driver: WebDriver, post: WebElement):
    action = ActionChains(driver)
    menu = post.find_element(By.XPATH, './/*[@aria-label="Actions for this post" and @role="button"]')
    scrolltarget(driver, menu)

    action.move_to_element(menu).click().perform()

    menuitem = WebDriverWait(driver, 3, 1).until(EC.presence_of_all_elements_located((By.XPATH, '//*[@role="menuitem"]')))
    wait(1)

    randomx, randomy = random.randint(0, 7), random.randint(0, 7)
    embed = None
    for i in menuitem:
        if "Embed" in i.text:
            embed = i
    if embed == None:
        wait(10000)
        return None, None
    dialog = (By.XPATH, './/*[@role="dialog" and @aria-label="Embed Post"]')
    vdialog = (By.XPATH, './/*[@role="dialog" and @aria-label="Embed Video"]')
    blockeddialog = (By.XPATH, './/*[@role="dialog"]//*[contains(text(),"Temporarily Blocked")]/ancestor::*[@role="dialog"][1]')
    
    action.move_to_element_with_offset(embed, randomx, randomy).click().perform()

    blockeddialog = trycatch(lambda: WebDriverWait(driver, 10, 2).until(EC.presence_of_element_located(blockeddialog)))

    if blockeddialog != None:
        print('embed is blocked')
        close_dialog(driver, action, blockeddialog)
        return None, None
    
    ptype='post'
    embeddialog = trycatch(lambda: WebDriverWait(driver, 10, 2).until(EC.presence_of_element_located(dialog)))
    if embeddialog == None:
        embeddialog = trycatch(lambda: WebDriverWait(driver, 10, 2).until(EC.presence_of_element_located(vdialog)))
        if embeddialog == None:
            print('embed dialog not found')
            return None, None
        ptype = 'video'
    post_link = embeddialog.find_element(By.XPATH, './/*[@type="text" and @dir="ltr"]').get_attribute('value')
    close_dialog(driver, action, embeddialog)
    return ptype, get_facebook_post_from_embed(post_link)
    
def share_technique(driver: WebDriver, post: WebElement):
    action = ActionChains(driver)

    share = post.find_element(By.XPATH, './/*[@role="button"]//*[contains(@data-ad-rendering-role,"share_button")]/ancestor::*[@role="button"][1]')
    
    scrolltarget(driver, share)

    action.move_to_element(share).click().perform()

    sdialog = (By.XPATH, './/*[@role="dialog"]//*[text()="Share"]/ancestor::*[@role="dialog"][1]')
    blockeddialog = (By.XPATH, './/*[@role="dialog"]//*[contains(text(),"Temporarily Blocked")]/ancestor::*[@role="dialog"][1]')

    blockeddialog = trycatch(lambda: WebDriverWait(driver, 10, 2).until(EC.presence_of_element_located(blockeddialog)))

    if blockeddialog != None:
        print('share is blocked')
        close_dialog(driver, action, blockeddialog)
        return None, None
    
    sharedialog = trycatch(lambda: WebDriverWait(driver, 10, 2).until(EC.presence_of_element_located(sdialog)))
    if sharedialog == None:
        time.sleep(19999)
        pass
    post_link = sharedialog.find_element(By.XPATH, './/a[@role="link" and @href and @attributionsrc]//*[contains(text(), "WhatsApp")]/ancestor::a[@role="link" and @href and @attributionsrc]').get_attribute('href')
    close_dialog(driver, action, sharedialog)
    return 'post', get_facebook_post_from_whatsapp_share(post_link)
def href_has_post_or_vid(e: WebElement):
    href = e.get_attribute('href')
    if "/post" in href:
        return 'post'
    if "/video" in href:
        return 'video'
    if "/live" in href:
        return 'live'
    return None
def convert_to_unix_timestamp(date_str:str):
    if date_str.strip() == '':
        return None
    # Define the format of the input string
    date_format = "%A, %B %d, %Y at %I:%M %p"
    
    # Convert the date string into a datetime object
    dt = datetime.strptime(date_str, date_format)
    
    # Get the Philippine timezone
    ph_time_zone = pytz.timezone("Asia/Manila")
    
    # Localize the datetime object to Philippine Time
    localized_dt = ph_time_zone.localize(dt)
    
    # Convert to Unix timestamp
    unix_timestamp = int(localized_dt.timestamp())
    
    return unix_timestamp
def facebook_post_engine(driver: WebDriver, fbpageurl: str):
    waiter = WebDriverWait(driver, 10, 2)

    action = ActionChains(driver)

    driver.get(fbpageurl)
    while not is_page_loaded(driver):
        time.sleep(1)

    postmap = lambda n: (By.XPATH, f'//div[@aria-posinset and @aria-describedby and @aria-labelledby and number(@aria-posinset) = {n}]//span[text()="Facebook"]/ancestor::div[@aria-posinset][1]')

    inset = 1

    while True:
        _link = None
        _type = None
        _unix = None
        post = waiter.until(EC.presence_of_element_located(postmap(inset)))
        scrolltarget(driver, post)
        try:
            reel = WebDriverWait(post, 2, 1).until(EC.presence_of_element_located((By.XPATH, f".//a[@role='link' and contains(@href, '/reel/') and @aria-label='Open reel in Reels Viewer']")))
        except:
            reel = None

        if reel != None:
            # it is a reel
            _link = reel.get_attribute('href')
            _link = _link.split('?')[0]
            _type = 'reel'
            try:
                current_month = datetime.now().strftime("%b").capitalize()
                hidden_span = WebDriverWait(post, 6, 2).until(EC.presence_of_element_located((By.XPATH, f".//span[contains(text(), '{current_month} ')]")))
                scrolltarget(driver, hidden_span)
                action.move_to_element(hidden_span).perform()
                wait(1.5)
                ptime = WebDriverWait(driver, 6, 2).until(EC.presence_of_element_located((By.XPATH, f".//div[@role='tooltip']/span[contains(text(), ', {current_year}') and parent::*[@role='tooltip']]")))
                _unix = convert_to_unix_timestamp(ptime.text)
            except Exception:
                pass
        else: 
            try:
                linkmap = (By.XPATH, f'.//a[@role="link" and contains(@attributionsrc, "privacy_sandbox") and contains(@href, "?__cft__")]')
                # print('Processing ', linkmap)
                hidden_as = WebDriverWait(post, 10, 2).until(EC.presence_of_all_elements_located(linkmap))
                for hidden_a in hidden_as:
                    p_image = hidden_a.find_elements(By.TAG_NAME, 'strong')
                    p_name = hidden_a.find_elements(By.TAG_NAME, 'image')
                    if p_image or p_name:
                        continue
                    scrolltarget(driver, hidden_a)
                    action.move_to_element(hidden_a).perform() # hover mouse
                    wait(3)
                    try:
                        _type = WebDriverWait(hidden_a, 6,2).until(href_has_post_or_vid)
                    except TimeoutException:
                        menu = post.find_element(By.XPATH, './/*[@aria-label="Actions for this post" and @role="button"]')
                        action.move_to_element(menu).perform()
                        wait(1)
                        continue

                    _link = hidden_a.get_attribute('href')
                    _link = _link.split('?')[0]
                    break

                if _link != None:
                    current_year = datetime.now().year
                    ptime = WebDriverWait(driver, 6, 2).until(EC.presence_of_element_located((By.XPATH, f".//div[@role='tooltip']/span[contains(text(), ', {current_year}') and parent::*[@role='tooltip']]")))
                    _unix = convert_to_unix_timestamp(ptime.text)

            except TimeoutException as te:
                print('TIMEOUT', te)
                pass
            except Exception as te:
                print('Exception', te)
                pass
        yield _link, _type, _unix
        inset += 1

def get_facebook_posts(driver: WebDriver, facebook_url: str) -> Generator[tuple[str, str], Any, Any]:
  
    waiter = WebDriverWait(driver, 10, 2)

    action = ActionChains(driver)

    driver.get(facebook_url)

    while not is_page_loaded(driver):
        time.sleep(1)
    
    postmap = lambda n: (By.XPATH, f'//div[@aria-posinset and @aria-describedby and @aria-labelledby and number(@aria-posinset) = {n}]//span[text()="Facebook"]/ancestor::div[@aria-posinset][1]')

    inset = 1

    is_embed_blocked = False

    elapsed_since_blocked = time.time()

    while True:

        if (time.time() - elapsed_since_blocked) >= 600: #10 minutes
            is_embed_blocked = False
            print("10 minutes have passed, retry using embed")

        post = waiter.until(EC.presence_of_element_located(postmap(inset)))

        scrolltarget(driver, post)

        keywords = tree_keyword_lookup('comments', post)
        for keyword in reversed(keywords):
            if re.search(r"\d+ comments", keyword):
                print('keyword', keyword)
                break

        try:
            reel = post.find_element(By.XPATH, ".//a[@role='link' and contains(@href, '/reel/') and @aria-label='Open reel in Reels Viewer']")
        except:
            reel = None

        if reel != None:
            # it is a reel
            reel_link = reel.get_attribute('href')
            yield 'reel', reel_link
        else:
            try: 
                # it is a post/video
                random_action = random.randint(0, 1)
                if random_action == 0:
                    if not is_embed_blocked:
                        print('via embed')
                        ptype, link = embed_technique(driver, post)
                        if link == None:
                            is_embed_blocked = True
                            elapsed_since_blocked = time.time()
                            print('try share')
                            ptype, link = share_technique(driver, post)
                    else :
                        print('via share')
                        ptype, link = share_technique(driver, post)
                    yield ptype, link
                elif random_action == 1:
                    print('via share')
                    ptype, link = share_technique(driver, post)
                    if link == None:
                        print('try embed')
                        ptype, link = embed_technique(driver, post)
                    yield ptype, link
            except Exception as exa:
                print('EXCEPTION ', exa)
                time.sleep(12131)
        inset += 1

def waitForSelector(
    driver: WebDriver | WebElement, strategy: str, selector: str
) -> WebElement:
    try:
        wait = WebDriverWait(driver, 60, 2)
        return wait.until(
            EC.visibility_of_element_located((strategy, selector))
        )
    except:
        return []  # type: ignore
    
def waitForPresence(
    driver: WebElement, strategy: str, selector: str
) -> list[WebElement]:
    try:
        wait = WebDriverWait(driver, 30)
        return wait.until(
            EC.presence_of_all_elements_located((strategy, selector))
        )
    except:
        return []

def force_delete_session(folder_path):
    try:
        shutil.rmtree(folder_path)  # Recursively delete folder and its contents
    except Exception:
        pass  # Ignore any exceptions that occur

def get_post_engagements(driver):

    comments = waitForSelector(
        driver,
        By.XPATH,
        "//span[@class='html-span xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x1hl2dhg x16tdsg8 x1vvkbs x1sur9pj xkrqix3']",
    )
    if comments != []:
        comments = comments.text
    if comments == []:
        comments = 0

    return {
            "comments": comments, 
        }
    


def get_vids_engagements(driver):

    comments = waitForSelector(
        driver,
        By.XPATH,
        "//span[@class='html-span xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x1hl2dhg x16tdsg8 x1vvkbs x1sur9pj xkrqix3']",
    )
    if comments != []:
        comments = comments.text
    if comments == []:
        comments = 0
    return {
            "comments": comments
        }

def get_live_engagements(driver):

    comments = waitForSelector(
        driver,
        By.XPATH,
        "//span[@class='html-span xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x1hl2dhg x16tdsg8 x1vvkbs x1sur9pj xkrqix3']",
    )
    if comments != []:
        comments = comments.text
    if comments == []:
        comments = 0

    return {
            "comments": comments, 
        }



def get_reels_engagements(driver):
    see_more = waitForSelector(driver, By.XPATH, "//div[@class='xdj266r x11i5rnm xat24cr x1mh8g0r x1vvkbs x126k92a']/div")
    see_more.click()
    engagements_html = waitForSelector(driver, By.XPATH, "//div[@class='xod5an3 x1mh8g0r xygnafs x1vjfegm']")
    reactions_html = waitForPresence(engagements_html, By.XPATH, "//span[@class='x193iq5w xeuugli x13faqbe x1vvkbs x1xmvt09 x1lliihq x1s928wv xhkezso x1gmr53x x1cpjm7i x1fgarty x1943h6x x4zkp8e x3x7a5m x1nxh6w3 x1sibtaa x1s688f x17z8epw']")

    comments = humanfriendly.parse_size(reactions_html[1].text, binary=False)
    return {
                "comments": comments
            }


def get_engagements(link: str, type: str):
    engagements = None
    try:
        sampler, session = generate_chrome_driver()
        sampler.get(link)
        while not is_page_loaded(sampler):
            time.sleep(1)
        print('final url', sampler.current_url)
        if "watch/live" in sampler.current_url:
            type = 'live'
        if type == 'post':
            post_sampler = WebDriverWait(sampler, 60, 2).until(EC.presence_of_element_located((By.XPATH, '//*[@role="dialog"]//div[@aria-posinset and @aria-describedby and @aria-labelledby and number(@aria-posinset) > 0]//span[text()="Facebook"]/ancestor::div[@aria-posinset][1]')))
            engagements = get_post_engagements(post_sampler)
        elif type == 'video':
            post_sampler = WebDriverWait(sampler, 60, 2).until(EC.presence_of_element_located((By.XPATH, '//*[@id="watch_feed"]')))
            engagements = get_vids_engagements(post_sampler)
        elif type == 'live':
            engagements = get_live_engagements(sampler)
            engagements['type'] = 'live'
        elif type == 'reel':
            engagements = get_reels_engagements(sampler)
    except:
        print('failed to extract engagements. probably due to wrong format or updated algorithm from Meta.')
    finally: 
        sampler.quit()
        force_delete_session(session)
        
    return engagements