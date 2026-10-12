import logging
import pathlib
import platform
import random
import sys
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchWindowException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

logging.basicConfig(format="[%(levelname)s] instagram-activities-wipe: %(message)s", level=logging.INFO)

# Do not edit
MODE = -1
CHECK_EVERY = -1
LIKES_URL = "https://www.instagram.com/your_activity/interactions/likes"
COMMENTS_URL = "https://www.instagram.com/your_activity/interactions/comments"

# Default: delete 20 comments/likes at once. You can change this if you want to delete more at once.
AT_ONCE_DELETE = 20

logging.info("Starting...")
try:
    # Start Chrome browser
    try:
        options = Options()
        # Store login in a Chrome profile
        if platform.system() == "Windows":
            wd = pathlib.Path().absolute()
            options.add_argument(f"user-data-dir={wd}\\chrome-profile")
        else:
            options.add_argument("user-data-dir=chrome-profile")
        driver = webdriver.Chrome(options=options)
    except:
        logging.error("Web driver could not start. Have you installed ChromeDriver? Check README for details")
        sys.exit(1)
    logging.info("Opened Chrome browser")

    while (mode := input("Enter 1 to wipe comments, 2 to wipe likes [1/2]: ").strip()) not in ["1", "2"]:
        pass
    MODE = int(mode)

    # Open Instagram comments/likes page
    if MODE == 1:
        driver.get(COMMENTS_URL)
        logging.info("Opening " + COMMENTS_URL)
    else:
        driver.get(LIKES_URL)
        logging.info("Opening " + LIKES_URL)

    # Sign in & Click 'Not now' on 'Save Your Login Info?' dialog
    while True:
        if driver.current_url.startswith(COMMENTS_URL if MODE == 1 else LIKES_URL):
            logging.info("Login detected")
            break
        try:
            logging.info("Waiting for sign in... (Please go to the browser and sign in. Don't click anything else after signing in!)")
            wait = WebDriverWait(driver, 60)

            def is_not_now_div_present(driver):
                try:
                    div = driver.find_element(By.CSS_SELECTOR, "div[role='button']")
                except:
                    return False
                return div.text == "Not now"

            wait.until(is_not_now_div_present)
            logging.info("Login detected")
            driver.find_element(By.CSS_SELECTOR, "div[role='button']").send_keys(Keys.ENTER)
            logging.info("Clicked 'Not now' on 'Save Your Login Info?'")
            break
        except TimeoutException:
            pass

    ITEM = "comment" if MODE == 1 else "like"
    ACTION = "Delete" if MODE == 1 else "Unlike"

    def leaf(text):
        # Leaf elements whose text is exactly `text`. Instagram's markup has no stable attributes for these.
        return driver.find_elements(By.XPATH, f'//*[not(*) and normalize-space(.)="{text}"]')

    def js_click(element):
        driver.execute_script("arguments[0].click();", element)

    def dump_page(name):
        # Save the page's HTML so broken selectors can be diagnosed
        path = pathlib.Path(name).absolute()
        path.write_text(driver.page_source, encoding="utf-8")
        logging.warning("Saved page HTML to " + str(path))

    # Main loop
    while True:
        # Click select button
        select_wait_count = 0
        while True:
            logging.info("Waiting for " + ITEM + "s to load...")
            time.sleep(2)
            if leaf("No results") or leaf("You haven't " + ("commented on" if MODE == 1 else "liked") + " anything"):
                logging.info("No " + ITEM + "s found. DONE. Quitting")
                driver.quit()
                sys.exit(0)
            if cancel := leaf("Cancel"):
                # Selection mode was left on. Reset it so every checkbox starts unticked
                js_click(cancel[0])
                logging.info("Clicked 'Cancel' to reset selection mode")
                continue
            if select := leaf("Select"):
                js_click(select[0])
                logging.info("Clicked 'Select'")
                break
            select_wait_count += 1
            if select_wait_count == 10:
                dump_page("debug_select.html")

        # Select all content
        selected_count = 0
        while_it_count = 0
        is_refreshed = False
        while selected_count == 0:
            if is_refreshed:
                break
            time.sleep(1)
            for i in driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="bulk_action_checkbox"]'):
                # Unticked checkboxes show the circle__outline icon
                if not i.find_elements(By.CSS_SELECTOR, '[style*="circle__outline"]'):
                    continue
                js_click(i.find_element(By.CSS_SELECTOR, '[aria-label="Toggle checkbox"]'))
                selected_count += 1
                logging.info("Selected a " + ITEM + " (Total: " + str(selected_count) + ")")
                if selected_count == AT_ONCE_DELETE:
                    break
            while_it_count += 1
            if while_it_count == 5 and selected_count == 0:
                dump_page("debug_items.html")
            if while_it_count > 10:
                if CHECK_EVERY == -1:
                    logging.warning("Are you seeing this popup -> 'There was a problem with removing some or all of your content. Try removing it again.' If so, it looks like you have reached the rate limit for remove operations. This is a server-side restriction from Instagram. You can: [1] quit the script now and run it later, or [2] leave it running and it will refresh the page every x hours to check if the rate limit is lifted, and continue unliking posts if it is. (Untested. It may or may not work.)")
                    while (choice := input("Your choice [1/2]: ")).strip() not in ["1", "2"]:
                        pass
                    if choice == "1":
                        logging.info("Quitting...")
                        driver.quit()
                        sys.exit(0)
                    while True:
                        hours_check_every = input("Check every x hour(s) (decimal is allowed, enter nothing to default to 1 hour) [x]: ")
                        try:
                            hours_check_every = float(hours_check_every or 1)
                            break
                        except:
                            pass
                    CHECK_EVERY = int(hours_check_every * 3600)
                    logging.info("Received. Will check every " + str(hours_check_every) + " hour(s). It might not be exact due to intentional randomization.")
                for i in driver.find_elements(By.CSS_SELECTOR, 'div[role="dialog"] button, div[role="dialog"] [role="button"]'):
                    if i.text.strip() == "OK":
                        js_click(i)
                        logging.info("Clicked 'OK' on 'Something went wrong' dialog")
                        break
                logging.info("Now we wait...")
                # randomize CHECK_EVERY by a variance of 10%
                time.sleep(random.uniform(CHECK_EVERY * 0.9, CHECK_EVERY * 1.1))
                logging.info(str(hours_check_every) + " hour(s) have passed. Refreshing the page...")
                driver.refresh()
                is_refreshed = True
                continue
        if is_refreshed:
            continue

        # Click delete
        time.sleep(1)
        action_buttons = driver.find_elements(By.CSS_SELECTOR, f'[role="button"][aria-label="{ACTION}"]') or leaf(ACTION)
        if not action_buttons:
            dump_page("debug_action.html")
            raise RuntimeError("Could not find the '" + ACTION + "' button")
        # This button ignores JavaScript clicks, so use a real one
        action_buttons[0].click()
        logging.info("Clicked '" + ACTION + "'")

        # Confirm delete
        is_clicked_confirmation = False
        confirm_wait_count = 0
        while not is_clicked_confirmation:
            time.sleep(1)
            for i in driver.find_elements(By.CSS_SELECTOR, 'div[role="dialog"] button, div[role="dialog"] [role="button"]'):
                if i.text.strip() == ACTION:
                    i.click()
                    logging.info("Clicked '" + ACTION + "' on confirmation dialog")
                    is_clicked_confirmation = True
                    break
            confirm_wait_count += 1
            if confirm_wait_count == 15 and not is_clicked_confirmation:
                dump_page("debug_confirm.html")
                raise RuntimeError("Could not find the '" + ACTION + "' confirmation dialog")

except KeyboardInterrupt:
    print()
    logging.info("Quitting on keyboard interrupt...")
    driver.quit()
    sys.exit(0)
except NoSuchWindowException:
    logging.exception("Browser window closed unexpectedly")
    sys.exit(1)
except Exception:
    logging.exception("Unknown error occurred")
    try:
        driver.quit()
    except:
        pass
    sys.exit(1)
