import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from openai_response import get_chatgpt_response
from concurrent.futures import ThreadPoolExecutor
import azure.cognitiveservices.speech as speechsdk
from pypinyin import pinyin, Style
import json

def is_ques( person, message ):
    flag = 0
    if person == '你' or person == 'You':
        return False
    if '?' in message or '？' in message:
        flag = 1
    elif '為何' in message or '什麼' in message or '哪' in message:
        flag = 1
    elif '幫我' in message or '如何' in message or '嗎' in message:
        flag = 1
    if flag == 1:
        return True
    else:
        return False

def capture_messages( chat_panel ):
    pre_messages = []
    pre_messages_len = []
    while True:
        messages = chat_panel.find_elements(By.XPATH, './/div[@class="Ss4fHf"]')
        tmp = pre_messages_len.copy()
        pre_messages_len = []
        for i in range(len(messages)):
            message = messages[i]
            contents = message.find_elements(By.XPATH, './/div[@jscontroller="RrV5Ic"]')
            pre_messages_len.append(len(contents))
            if message in pre_messages and len(contents) == tmp[i]:
                continue
            person = message.find_element(By.XPATH, './/div[@class="poVWob"]').text # 帳號名
            #timestamp = message.find_element(By.XPATH, './/div[@class="MuzmKe"]').text  # 時間戳
            if message in pre_messages:
                for j in range(tmp[i], len(contents)):
                    content = contents[j]
                    content = content.text
                    #print(f"{person} [{timestamp}]: {content}")
                    if is_ques(person, content):
                        # 傳送到 ChatGPT
                        bot_response = get_chatgpt_response(content)
                        print(f"ChatGPT 回應: {bot_response}")

                        try:
                            # 發送回 Google Meet 聊天
                            if( bot_response != "無法處理訊息" ):
                                send_message_to_meet( driver, bot_response )
                        except Exception as e:
                            print(f"出錯: {e}")
            else:
                for content in contents:
                    content = content.text
                    #print(f"{person} [{timestamp}]: {content}")
                    if is_ques(person, content):
                        # 傳送到 ChatGPT
                        bot_response = get_chatgpt_response(content)
                        print(f"ChatGPT 回應: {bot_response}")

                        try:
                            # 發送回 Google Meet 聊天
                            if( bot_response != "無法處理訊息" ):
                                send_message_to_meet( driver, bot_response )
                        except Exception as e:
                            print(f"出錯: {e}")
        pre_messages = messages.copy()
        
        time.sleep(30)

def send_message_to_meet( driver, message ):
    chat_input = driver.find_element(By.XPATH, "//textarea[@aria-label='傳送訊息給所有人']")
    driver.execute_script("""
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
    """, chat_input, message)
    chat_input.send_keys(Keys.RETURN)

def transcribe_audio( API_Key, Region, Name, DEVICE, driver ):
    # Azure Speech 設置
    speech_config = speechsdk.SpeechConfig( subscription=API_Key, region=Region )
    # 設置識別語言
    speech_config.speech_recognition_language = "zh-TW"  # 繁體中文
    audio_config = speechsdk.audio.AudioConfig( device_name=DEVICE )  # 指定虛擬音頻設備
    speech_recognizer = speechsdk.SpeechRecognizer( speech_config=speech_config, audio_config=audio_config )

    # 實時轉錄
    print( "Listening..." )

    class ResultHandler:
        def __init__(self, roll_call):
            self.roll_call = roll_call

        # 檢查兩個詞是否同音
        def is_homophone(self, word1, word2):
            pinyin1 = pinyin(word1, style=Style.NORMAL)
            pinyin2 = pinyin(word2, style=Style.NORMAL)
            if pinyin1[0] not in pinyin2:
                return False
            else:
                for i in range( len(pinyin2) ):
                    if pinyin2[i] == pinyin1[0]:
                        for j in range( len(pinyin1) ):
                            if pinyin1[j] == pinyin2[i+j] and j == len(pinyin1)-1:
                                return True
                            if pinyin1[j] != pinyin2[i+j]:
                                break
            return False
        
        def handle_result(self, evt):
            print( evt.result.text )
            if self.is_homophone("點名", evt.result.text):
                self.roll_call = 1
                print( "roll call" )
            if self.roll_call == 1 and self.is_homophone(Name, evt.result.text):
                send_message_to_meet( driver, "在" )
            if is_ques( '', evt.result.text ):
                response = get_chatgpt_response( evt.result.text )
                if( response != "無法處理訊息" ):
                    time.sleep( 30 )
                    send_message_to_meet( driver, response )

    roll_call = 0
    handler = ResultHandler( roll_call=roll_call )
    speech_recognizer.recognized.connect( handler.handle_result )
    speech_recognizer.start_continuous_recognition()
    input( "Press Enter to stop...\n" )
    speech_recognizer.stop_continuous_recognition()

def task1( chat_panel ):
    capture_messages( chat_panel )

def task2( API_KEY, API_REGION, NAME, DEVICE, driver ):
    transcribe_audio( API_KEY, API_REGION, NAME, DEVICE, driver )

if __name__ == "__main__":
    # 讀取 JSON 檔案
    with open("data.json", "r", encoding="utf-8") as file:
        data = json.load(file)
    
    GOOGLE_EMAIL = data[0]["GOOGLE_EMAIL"]
    GOOGLE_PASSWORD = data[0]["GOOGLE_PASSWORD"]
    room_id = data[0]["ROOM_ID"]
    GOOGLE_MEET_URL = "https://meet.google.com/" + room_id  # 替換為你的會議連結
    API_KEY = data[0]["SPEECH_API"]
    API_REGION = data[0]["SPEECH_REGION"]
    NAME = data[0]["STUDENT_NAME"]
    DEVICE = data[1]["Endpoint"]
    
    # 設置 WebDriver
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)  # 確保瀏覽器不會因程式結束而關閉
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")  # 隱藏自動化痕跡
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.96 Safari/537.36")
    driver = webdriver.Chrome(options=options)

    try:
        # 登入 Google
        driver.get("https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Faccounts.google.com%2F&followup=https%3A%2F%2Faccounts.google.com%2F&ifkv=AcMMx-ebqwjve9MKsJ0Mp406yy1GIdE-bXKGCev9VhMfTPDNiZGZZiQhoOxwof5VJopvt0YYPBXFGQ&passive=1209600&flowName=GlifWebSignIn&flowEntry=ServiceLogin&dsh=S1242508675%3A1733555458747921&ddm=1")
        if GOOGLE_EMAIL:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "identifierId"))
            ).send_keys(GOOGLE_EMAIL + Keys.RETURN)
        if GOOGLE_PASSWORD:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "Passwd"))
            ).send_keys(GOOGLE_PASSWORD + Keys.RETURN)

        # 進入 Google Meet
        WebDriverWait(driver, 540).until(
            EC.url_contains("myaccount.google.com")  # 確保登入成功
        )
        driver.get(GOOGLE_MEET_URL)

        # 打開 Google Meet 討論區
        WebDriverWait(driver, 540).until(
            EC.presence_of_element_located((By.XPATH, '//button[@aria-label="與所有參與者進行即時通訊"]'))
        ).click()

        # 持續擷取討論區訊息
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '//div[@class="Ge9Kpc z38b6"]'))
        )
        print("開始擷取討論區訊息...")
        chat_panel = driver.find_element(By.XPATH, '//div[@class="Ge9Kpc z38b6"]')  # 討論區訊息容器
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit( task1, chat_panel )
            executor.submit( task2, API_KEY, API_REGION, NAME, DEVICE, driver )
    except Exception as e:
        print(f"發生錯誤: {e}")


