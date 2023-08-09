import sys

import requests
from bs4 import BeautifulSoup
from PIL import Image
from PIL import ImageFile
from tqdm import tqdm
import os
import shutil
from retrying import retry

Image.MAX_IMAGE_PIXELS = None  # 禁用解压缩炸弹限制
ImageFile.LOAD_TRUNCATED_IMAGES = True  # 损坏的图片

folder_temp = "temp"
folder_output = "OutPut"

url = "https://baozimh.org/chapterlist/wufashengjidewanjia-taeaparrotkimgavingereddogculturehouse"


@retry(stop_max_attempt_number=3, wait_fixed=1000)
def comb(png1, png2, style='horizontal'):
    img1, img2 = Image.open(png1), Image.open(png2)
    # 统一图片尺寸，可以自定义设置（宽，高）
    # img1 = img1.resize((1500, 1000), Image.LANCZOS)
    # img2 = img2.resize((1500, 1000), Image.LANCZOS)
    size1, size2 = img1.size, img2.size
    if style == 'horizontal':
        joint = Image.new('RGB', (size1[0] + size2[0], size1[1]))
        loc1, loc2 = (0, 0), (size1[0], 0)
        joint.paste(img1, loc1)
        joint.paste(img2, loc2)
        joint.save(f'./{folder_temp}/horizontal.png')
    elif style == 'vertical':
        joint = Image.new('RGB', (size1[0], size1[1] + size2[1]))
        loc1, loc2 = (0, 0), (0, size1[1])
        joint.paste(img1, loc1)
        joint.paste(img2, loc2)
        joint.save(f'./{folder_temp}/vertical.png')


@retry(stop_max_attempt_number=3, wait_fixed=1000)
def download():
    if not os.path.exists(f"./{folder_temp}"):
        os.mkdir(f"./{folder_temp}")

    list_href = []
    # 读取所有章节链接
    if os.path.exists(f"./{folder_temp}/{url.strip('/').split('/')[-1]}.txt"):
        print("读取章节链接缓存")
        with open(f"./{folder_temp}/{url.strip('/').split('/')[-1]}.txt", 'rb') as f:
            list_href = f.read().decode('utf-8').split('\n')
    else:
        req = requests.get(url=url)
        soup = BeautifulSoup(req.content, 'html.parser')
        for link in tqdm(soup.find_all("a", "wp-manga-chapterlist"), "获取所有章节链接"):
            list_href.append(link.get('href'))
        list_href = list(reversed(list_href))
        with open(f"./{folder_temp}/{url.strip('/').split('/')[-1]}.txt", 'wb') as f:
            f.write('\n'.join(list_href).__str__().encode('utf-8'))

    dict_all_href = {}
    if os.path.exists(f"./{folder_temp}/{url.strip('/').split('/')[-1]}_img.txt"):
        print("读取图片链接缓存")
        with open(f"./{folder_temp}/{url.strip('/').split('/')[-1]}_img.txt", 'rb') as f:
            dict_all_href = eval(f.read().decode('utf-8'))
    else:
        for link in tqdm(list_href, desc="获取图片链接"):
            list_img_href = []
            req = requests.get(url=link)
            soup = BeautifulSoup(req.content, 'html.parser')
            for img in soup.find(id="page").find_all("img"):
                if img.get('data-src') is not None:
                    list_img_href.append(img.get('data-src'))
                else:
                    list_img_href.append(img.get('src'))
                list_img_href = [x for i, x in enumerate(list_img_href) if x not in list_img_href[:i]]
            dict_all_href[link] = list_img_href
        with open(f"./{folder_temp}/{url.strip('/').split('/')[-1]}_img.txt", 'wb') as f:
            f.write(str(dict_all_href).encode('utf-8'))

    if not os.path.exists(f"./{folder_output}"):
        os.mkdir(f"./{folder_output}")
    if not os.path.exists(f"./{folder_temp}/temp"):
        os.mkdir(f"./{folder_temp}/temp")

    list_href_downloaded = []
    # 读取downloaded缓存
    if os.path.exists(f"./{folder_temp}/{url.strip('/').split('/')[-1] + '_downloaded'}.txt"):
        print("读取读取downloaded缓存缓存")
        with open(f"./{folder_temp}/{url.strip('/').split('/')[-1] + '_downloaded'}.txt", 'rb') as f:
            list_href_downloaded = f.read().decode('utf-8').split('\n')

    for link in list_href:
        print(f"\r\n下载章节：{link}")
        if link.strip() in list_href_downloaded:
            print(f"{link}已存在，跳过")
            continue
        count = 0
        for link_img in tqdm(dict_all_href[link], desc=f"下载图片"):
            response = requests.get(link_img)
            with open(f"./{folder_temp}/temp/{count}.png", 'wb') as f:
                f.write(response.content)
                count += 1
        combine_images(link, count)


@retry(stop_max_attempt_number=3, wait_fixed=1000)
def combine_images(link, count):
    is_first = True
    old_count = count
    if old_count & 1:
        count -= 1
    while count > 0:
        new_count = 0
        for i in tqdm(range(0, count), desc="合并图片"):
            if i & 1:
                continue
            file_path = "/"
            if is_first:
                file_path = "/temp/"
            comb(f"./{folder_temp}{file_path}{i}.png", f"./{folder_temp}{file_path}{i + 1}.png", style='vertical')
            if not is_first:
                os.remove(f"./{folder_temp}/{i}.png")
                os.remove(f"./{folder_temp}/{i + 1}.png")
            os.replace(f"./{folder_temp}/vertical.png", f"./{folder_temp}/{new_count}.png")
            count -= 1
            new_count += 1
        if old_count & 1:
            os.rename(f"./{folder_temp}{file_path}{old_count - 1}.png",
                      f"./{folder_temp}/{int((old_count - 1) / 2)}.png")
        old_count = int((old_count + 1) / 2)
        is_first = False
    os.rename(f"./{folder_temp}/0.png", f"./{folder_temp}/{link.strip('/').split('/')[-1]}.png")
    shutil.move(f"./{folder_temp}/{link.strip('/').split('/')[-1]}.png", f"./{folder_output}/")
    os.remove(f"./{folder_temp}/temp/")
    with open(f"./{folder_temp}/{url.strip('/').split('/')[-1] + '_downloaded'}.txt", 'ab') as f:
        f.write((link.__str__()).encode('utf-8'))
        f.write("\n".encode("utf-8"))


if len(sys.argv) > 1:
    url = sys.argv[1]
    download()
else:
    download()
