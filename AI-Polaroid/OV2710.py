import cv2
import time
import threading
import logging
import qrcode.constants
import requests
import json
import os
import numpy as np
import queue
from PIL import Image
import subprocess
import io


from alibabacloud_facebody20191230.client import Client as Client_anime
from alibabacloud_facebody20191230.models import GenerateHumanAnimeStyleAdvanceRequest
from alibabacloud_facebody20191230.models import EnhanceFaceAdvanceRequest
from alibabacloud_tea_util.models import RuntimeOptions
from alibabacloud_tea_openapi.models import Config

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import GappedSquareModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask 

class FlagManager:

    def __init__ (self, **flags):
        self.flags = {key: value for key, value in flags.items()}
    
    def set_flag(self, flag_name, value = True):
        self.flags[flag_name] = value

    def get_flag(self, flag_name):
        return self.flags.get(flag_name, False)

    def toggle_flag(self, flag_name):
        self.flags[flag_name] = not self.flags.get(flag_name, False)

    def clear_flag(self, flag_name):
        self.flags[flag_name] = False

    def __str__(self):
        return set(self.flags)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

anime_config = Config(
    access_key_id ="", #please input your access key id and secret key
    access_key_secret ="", #please input your access key id and secret key

    endpoint = "facebody.cn-shanghai.aliyuncs.com",
    region_id = "cn-shanghai"
)

flag_manager = FlagManager(
    VanceAI_anime_style3_flag = False,
    ali_anime_flag = False,
    VanceAI_anime_disney_flag = False,
    cv2_show_flag = False,
    process_flag = False
)

show_lock = threading.Lock()
show_flag = 0

show_details_queue = queue.Queue()

printer_name = 'Mi_Wireless_Photo_Printer_1S' #  please input your printer name

def print_file(printer_name, file_path):

    result = subprocess.run(['lp', '-d', printer_name, file_path], capture_output=True, text=True, check=True)
    if result.returncode == 0:
        logging.info("打印成功")
    else:
        logging.error("打印失败")


def display():
    try:
        global flag_manager
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            logging.error("无法打开摄像头")

        desired_width = 1280 # 1920 1280
        desired_height = 720 # 1080 720
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, desired_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, desired_height)

        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        logging.info(f"当前分辨率：{int(width)} x {int(height)}")

        if width != desired_width or height != desired_height:
            logging.warning(f"摄像头不支持设置的分辨率：{desired_width} x {desired_height}, 实际的分辨率是：{int(width)} x {int(height)}")

        cv2.namedWindow('image', cv2.WINDOW_NORMAL)
        cv2.setWindowProperty('image', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.setWindowProperty('image', cv2.WND_PROP_VISIBLE, 0)


        while True:

            if flag_manager.get_flag('process_flag') == True:
                image = cv2.imread('./process.jpg')
                cv2.imshow('image', image)
                cv2.waitKey(1)
                continue


            
            ret, image = cap.read()
            if not ret:
                logging.error("无法获取帧")
                continue

            
            flipped_image = cv2.flip(image, 1) 

           
            if flag_manager.get_flag('cv2_show_flag') == True:
                image =  show_details_queue.get()
                logging.info("拿到处理拼接的图像")
                flag_manager.set_flag('cv2_show_flag', False)

                show_details_queue.queue.clear()

                cv2.imshow('image', image)
                logging.info("展示图像完成")
                key = cv2.waitKey(0) & 0xFF
                if key == ord('1'):
                    print_file(printer_name, './picture/ali_face_and_qr.jpg')
                elif key == ord('2'):
                    print_file(printer_name, './picture/vanceAI_anime_and_qr.jpg')
                elif key == ord('3'):
                    print_file(printer_name, './picture/ali_anime_and_qr.jpg')
                elif key == ord('4'):
                    print_file(printer_name, './picture/vanceAI_disney_and_qr.jpg')
                delete_file()

                if key == 8:
                    
                    continue

            
            cv2.imshow('image', flipped_image)
            # cv2.waitKey(1)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('0'):

                flag_manager.set_flag('process_flag', True)


                cv2.imwrite('./picture/original.jpg', flipped_image)

                logging.info("原始图像保存成功")

                
                ali_face('./picture/original.jpg')

                logging.info("开始设置API的标志位")
                
                flag_manager.set_flag('VanceAI_anime_style3_flag', True)
                
                flag_manager.set_flag('ali_anime_flag', True)
                
                flag_manager.set_flag('VanceAI_anime_disney_flag', True)



    except Exception as e:
        logging.error(f"发生错误：{e}")
    finally:
        cap.release()



def VanceAI_Style3():

    global flag_manager
    global show_flag
    time_pos = 0
    while True:
        try:

            if flag_manager.get_flag('VanceAI_anime_style3_flag') == False:
                time.sleep(0.1)
                continue

            json_path = './Style3.json'
            api_token = '25b148ecfc76761e1cc0722ea3991279' #place your api token here
            image_path = './picture/original.jpg'
            qr_path = './picture/vanceAI_style3_qr.jpg'
            picture_path = './picture/vanceAI_style3.jpg'
            VanceAI_anime(json_path, api_token, image_path, qr_path, picture_path)

            
            flag_manager.set_flag('VanceAI_anime_style3_flag', False)
            
            with show_lock:
                show_flag |= 0x01
        
        except Exception as e:
            time_pos += 1
            if time_pos > 2:
                logging.error("VanceAI anime 请求超时失败")
                
                time_pos = 0
                
                flag_manager.set_flag('VanceAI_anime_style3_flag', False)
                with show_lock:
                    show_flag |= 0x01
            else:
                logging.error(f"VanceAI anime发生错误：{e}")


def ali_face(image_path):
    image = open(image_path, "rb")

    face_response = EnhanceFaceAdvanceRequest()
    face_response.image_urlobject = image

    runtime_options = RuntimeOptions()

    face_config = Client_anime(anime_config)
    try:
        
        face_response = face_config.enhance_face_advance(face_response, runtime_options)
    except Exception as e:
        logging.error(f"ali face API 调用出错：{e}")
    
    generate_qrcode(face_response.body.data.image_url, './picture/ali_face_qr.jpg')
    
   
    ali_face_response = requests.get(face_response.body.data.image_url)
    if ali_face_response.status_code == 200:
        image_data = io.BytesIO(ali_face_response.content)
        with Image.open(image_data) as image:
            target_size = (1920, 1080)
            image = image.resize(target_size)
            image.save('./picture/ali_face.jpg', 'JPEG')


def ali_anime():
    global flag_manager
    global show_flag
    time_pos = 0
    while True:
            try:
                if flag_manager.get_flag('ali_anime_flag') == False:
                    time.sleep(0.1)
                    continue

                original_image = open('./picture/ali_face.jpg', 'rb')

                generate_human_request = GenerateHumanAnimeStyleAdvanceRequest()
                generate_human_request.image_urlobject = original_image
                generate_human_request.algo_type = "comic"

                runtime_options = RuntimeOptions()
                anime_client = Client_anime(anime_config)
                try:
                    
                    anime_response = anime_client.generate_human_anime_style_advance(generate_human_request, runtime_options)
                except Exception as e:
                    logging.error(f"ali anime API 调用出错：{e}")

                
                generate_qrcode(anime_response.body.data.image_url, './picture/ali_anime_qr.jpg')
                
                
                anime_response_request = requests.get(anime_response.body.data.image_url)
                if anime_response_request.status_code == 200:
                    with open(r'./picture/ali_anime.jpg', 'wb') as f:
                        f.write(anime_response_request.content)
                        logging.info('ali anime图像保存成功')
            
                
                flag_manager.set_flag('ali_anime_flag', False)
                with show_lock:
                    show_flag |= 0x02

            except Exception as e:
                time_pos += 1
                if time_pos > 2:
                    logging.error("ali anime 请求超时失败")
                    
                    time_pos = 0
                    
                    flag_manager.set_flag('ali_anime_flag', False)
                    with show_lock:
                        show_flag |= 0x02
                else:
                    logging.error(f"ali anime 发生错误：{e}")



def VanceAI_disney():
    global flag_manager
    global show_flag
    time_pos = 0
    while True:
        try:
            if flag_manager.get_flag('VanceAI_anime_disney_flag') == False:
                time.sleep(0.1)
                continue
            json_path = "./disney.json"
            api_token = "25b148ecfc76761e1cc0722ea3991279" #place your api token here
            image_path = "./picture/original.jpg"
            qr_path = './picture/vanceAI_disney_qr.jpg'
            picture = './picture/vanceAI_disney.jpg'
            VanceAI_anime(json_path, api_token, image_path, qr_path, picture)

            
            flag_manager.set_flag('VanceAI_anime_disney_flag', False)
            
            with show_lock:
                show_flag |= 0x04
        except Exception as e:
            time_pos += 1
            if time_pos > 2:
                logging.error("VanceAI_disney 请求超时失败")
               
                time_pos = 0
                
                flag_manager.set_flag('VanceAI_anime_disney_flag', False)
                with show_lock:
                    show_flag |= 0x04
            else:
                logging.error(f"VanceAI_disney 发生错误：{e}")

def process_picture():

    global flag_manager
    global show_flag
    while True:
        
        if show_flag & 0x01 and show_flag & 0x02 and show_flag & 0x04:
            with show_lock:

                target_size = (640, 360)
                canvas = np.zeros((1080, 1920, 3), dtype=np.uint8)

                if os.path.exists("./picture/ali_face.jpg") and os.path.exists("./picture/ali_face_qr.jpg"):
                    
                    ali_face_image = cv2.imread("./picture/ali_face.jpg")
                    ali_face_image = cv2.resize(ali_face_image, target_size)
                    canvas[:360, :640] = ali_face_image
                    paste_image('./picture/ali_face.jpg', './picture/ali_face_qr.jpg', './OpenELAB.jpg', './logo0.jpg', './picture/ali_face_and_qr.jpg')
                    logging.info("ali face展示图像生成成功")
                else:
                    logging.error("ali face展示图像生成失败")

               
                if os.path.exists("./picture/vanceAI_style3.jpg") and os.path.exists("./picture/vanceAI_style3_qr.jpg"):
                    
                    vanceAI_anime_image = cv2.imread("./picture/vanceAI_style3.jpg")
                    vanceAI_anime_image = cv2.resize(vanceAI_anime_image, target_size)
                    canvas[:360, 640:1280] = vanceAI_anime_image
                    paste_image('./picture/vanceAI_style3.jpg', './picture/vanceAI_style3_qr.jpg', './OpenELAB.jpg', './logo0.jpg', './picture/vanceAI_anime_and_qr.jpg')
                    logging.info("vanceAI展示图像生成成功")
                else:
                    logging.error("vanceAI展示图像生成失败")

                if os.path.exists("./picture/ali_anime.jpg") and os.path.exists("./picture/ali_anime_qr.jpg"):
                    
                    aliAI_anime_image = cv2.imread("./picture/ali_anime.jpg")
                    aliAI_anime_image = cv2.resize(aliAI_anime_image, target_size)
                    canvas[:360, 1280:1920] = aliAI_anime_image
                    paste_image('./picture/ali_anime.jpg', './picture/ali_anime_qr.jpg', './OpenELAB.jpg', './logo0.jpg', './picture/ali_anime_and_qr.jpg')
                    logging.info("ali展示图像生成成功")
                else:
                    logging.error("ali展示图像生成失败")
                
                if os.path.exists('./picture/vanceAI_disney.jpg') and os.path.exists('./picture/vanceAI_disney_qr.jpg'):
                    
                    vanceAI_disney_image = cv2.imread("./picture/vanceAI_disney.jpg")
                    vanceAI_disney_image = cv2.resize(vanceAI_disney_image, target_size)
                    canvas[720:1080, :640] = vanceAI_disney_image
                    paste_image('./picture/vanceAI_disney.jpg', './picture/vanceAI_disney_qr.jpg', './OpenELAB.jpg', './logo0.jpg', './picture/vanceAI_disney_and_qr.jpg')
                    logging.info("vanceAI_disney展示图像生成成功")
                else:
                    logging.error("vanceAI_disney展示图像生成失败")

                flag_manager.set_flag('cv2_show_flag', True)

                cv2.imwrite("./picture/canvas.jpg", canvas)

                show_details_queue.put(canvas)
                logging.info("处理后的图像发送完成")
                show_flag = 0
                flag_manager.set_flag('process_flag', False)


def VanceAI_anime(json_path, api_token, image_path, qr_path, picture_path):
    response = requests.post(
        'https://api-service.vanceai.com/web_api/v1/upload',
        files = {'file' : open(image_path, 'rb')},
        data = {'api_token' : api_token}
    )
    r = response.json()
    if r['code'] == 200:
        logging.info("VanceAI 图像上传成功")
    else:
        logging.error("VanceAI图像上传失败")
        logging.error(r['code'])

    jparam = {}
    with open(json_path, 'rb') as f:
        jparam = json.load(f)
    
    data = {
        'api_token' : api_token,
        'uid' : r['data']['uid'],
        'jconfig' : json.dumps(jparam),
    }
    response = requests.post(
        'https://api-service.vanceai.com/web_api/v1/transform',
        data
    )
    r = response.json()
    if r['code'] == 200:
        logging.info("VanceAI 图像转换成功")
    else:
        logging.error("VanceAI图像转换失败")
    
    remoteFileUrl = 'https://api-service.vanceai.com/web_api/v1/download?' + 'trans_id=' + r['data']['trans_id'] + '&api_token=' + api_token

    generate_qrcode(remoteFileUrl, qr_path)

    response = requests.get(remoteFileUrl, stream=True)

    with open(picture_path, 'wb') as f:
        f.write(response.content)


def generate_qrcode(url, output_file = "qrcode.png"):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=2,
        border=1
    )
     
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(
        fill_color = 'black',
        back_color = 'white',
        image_factory = StyledPilImage,
        module_drawer = GappedSquareModuleDrawer(),
        color_mask = SolidFillColorMask(front_color = (0, 0, 0), back_color = (255, 255, 255))
    )

    img = img.resize((168, 168))
    
    img.save(output_file)
    logging.info("二维码生成成功")



def paste_image(image1_path, image2_path, OpenELAB_path, logo_path, output_file):
    img1 = Image.open(image1_path)

    img2 = Image.open(image2_path)

    img3 = Image.open(OpenELAB_path)

    img4 = Image.open(logo_path)

    img1_width, img1_height = img1.size

    img2_width, img2_height = img2.size

    img3_width, img3_height = img3.size

    img4_width, img4_height = img4.size

    new_img_height = img1_height + max(img2_height, img3_height , img4_height)

    new_img = Image.new('RGB', (img1_width, new_img_height), (255, 255, 255))

    new_img.paste(img1, (0, 0))
    new_img.paste(img2, (int(img1_width / 2) + int(img4_width / 2) + 100, img1_height))
    new_img.paste(img3, (int(img1_width / 2) - img3_width - int(img4_width / 2) - 100, img1_height))
    new_img.paste(img4, (int(img1_width / 2) - int(img4_width / 2) , img1_height))

    new_img.save(output_file)
    logging.info("图像拼接成功")

def delete_file():
    result = subprocess.run('rm -fr ./picture/*', shell=True, capture_output=True, check=True)
    if result.returncode == 0:
        logging.info("文件删除成功")
    else:
        logging.error("文件删除失败")


def main():


    display_thread = threading.Thread(target=display)
    display_thread.daemon = True
    display_thread.start()

    VanceAI_anime_style3_thread = threading.Thread(target=VanceAI_Style3)
    VanceAI_anime_style3_thread.daemon = True
    VanceAI_anime_style3_thread.start()

    VanceAI_anime_disney_thread = threading.Thread(target=VanceAI_disney)
    VanceAI_anime_disney_thread.daemon = True
    VanceAI_anime_disney_thread.start()

    ali_anime_thread = threading.Thread(target=ali_anime)
    ali_anime_thread.daemon = True
    ali_anime_thread.start()

    process_picture_thread = threading.Thread(target=process_picture)
    process_picture_thread.daemon = True
    process_picture_thread.start()

    while True:
        time.sleep(1)

    
if __name__ == "__main__":
    main()

