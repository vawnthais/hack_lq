import requests
import sys
from urllib.parse import urlparse, parse_qs

sys.stdout.reconfigure(encoding='utf-8')

url = "https://kgvn-camp.mobagarena.com/app/player-poster?isLowDevice=false&lang=VN&partition=1011&aov_areaid=1&aov_region=1137&from=aov&orientation=landscape&access_token=6a2d317c5e854b15364040168b5acf7a361321524eae59f6d2bd71b9f5338d5f&algorithm=itop&encode=2&channelid=10&nickname=Rush%20B%20rush%20B&gameid=1137&os=1&ts=1785512914&version=null&seq=1137-0c934b77-4208-4da5-8c0b-f2da052a3c89-1785512914-223065&sig=5651518cf32f4d791d0c9936dd885cd9&itopencodeparam=1B1781C90F106F635BC7FBFE83393D977BAF6EE9E62FCEBFCAF59367ED385B85CE1067CCF4397791DB6530BA12FD96FAA54F22B396E6A77065D3F1EF8C3BA27B3FAB978B3E9D6DF6685D1AFAE9DED0ECB2202FB7C5317A30A3B99A0337FFC75F4C898E9BCAC846CC6AA53099AC3CA09C725D5E7A3B187045E6085041FEA1C820"

parsed = urlparse(url)
params = parse_qs(parsed.query)

def get_param(key):
    return params.get(key, [''])[0]

headers = {
    'accept': '*/*',
    'accept-language': 'vi,en;q=0.9',
    'aov-language': 'VN',
    'aov-region': get_param('aov_region'),
    'areaid': get_param('aov_areaid'),
    'camp-authtype': 'msdk',
    'camp-source': 'AOV-CAMP',
    'content-type': 'application/json',
    'logicworldid': get_param('partition'),
    'msdk-channelid': get_param('channelid'),
    'msdk-gameid': get_param('gameid'),
    'msdk-itopencodeparam': get_param('itopencodeparam') or get_param('access_token'),
    'msdk-os': get_param('os'),
    'origin': 'https://kgvn-camp.mobagarena.com',
    'referer': 'https://kgvn-camp.mobagarena.com/',
    'user-agent': 'Mozilla/5.0'
}

print("1. getselfuserinfo")
r1 = requests.post('https://kgvn-api.mobagarena.com/api/user/game/getselfuserinfo', headers=headers, json={})
print(r1.json())
encodeparam = r1.json().get('data', {}).get('encryption')
if encodeparam:
    headers['encodeparam'] = encodeparam

print("2. createposter")
r2 = requests.post('https://kgvn-api.mobagarena.com/api/game/poster/playerimage/createposter', headers=headers, json={})
print(r2.json())
poster_id = r2.json().get('data', {}).get('posterId')

if poster_id:
    print("3. getcoscredential")
    r3 = requests.post('https://kgvn-api.mobagarena.com/api/game/poster/getcoscredential', headers=headers, json={
        "scene": "PlayerimagePoster",
        "fileName": f"0/1/{poster_id}.png"
    })
    print(r3.json())
    cred = r3.json().get('data', {})
    
    # Extract base path for saveposter
    key = cred.get('path', '')
    base_path = key.split('0/1/')[0] if '0/1/' in key else key
    pic_url = f"{cred.get('cdnHost', '').rstrip('/')}{base_path}"
    if not pic_url.endswith('/'):
        pic_url += '/'
        
    print("\n3.5 Upload to COS")
    from qcloud_cos import CosS3Client, CosConfig
    config = CosConfig(Region=cred['region'], SecretId=cred['tmpSecretId'], SecretKey=cred['tmpSecretKey'], Token=cred['token'])
    client = CosS3Client(config)
    bucket = f"{cred['appId']}" if '-' in cred['bucket'] else f"{cred['bucket']}-{cred['appId']}"
    
    # Create a valid 320x504 PNG in memory
    from PIL import Image
    import io
    img = Image.new('RGB', (320, 504), color = (73, 109, 137))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    client.put_object(
        Bucket=bucket,
        Body=img_byte_arr,
        Key=cred['path'],
        EnableMD5=False,
        ContentType='image/png'
    )
    print("Upload success!")
    
    import time
    time.sleep(2)

    print("\n4. saveposter")
    payload = {
        "posterId": str(poster_id),
        "isApply": True,
        "isShare": True,
        "picUrl": pic_url,
        "picInfo": {
            "bg": {
                "id": "12",
                "picUrl": "https://kg-camp.mobagarena.com/manage/playerimage_official/M3lFCxKR.png",
                "source": 1,
                "width": 320,
                "height": 504,
                "posX": 0,
                "posY": 0
            },
            "stickerList": []
        }
    }
    
    r4 = requests.post('https://kgvn-api.mobagarena.com/api/game/poster/playerimage/saveposter', headers=headers, json=payload)
    print(r4.json())
