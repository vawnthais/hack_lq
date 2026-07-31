import re
from urllib.parse import urlparse, parse_qs
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests

app = Flask(__name__, static_folder='static')
CORS(app)

TARGET_API_URL = 'https://kgvn-api.mobagarena.com/api/game/poster/playerimage/saveposter'
USER_INFO_API_URL = 'https://kgvn-api.mobagarena.com/api/user/game/getselfuserinfo'

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/api/user-info', methods=['POST'])
def get_user_info():
    try:
        data = request.json or {}
        webview_url = data.get('webview_url', '').strip()
        if not webview_url:
            return jsonify({'success': False, 'message': 'Thiếu Webview URL'}), 400

        parsed_url = urlparse(webview_url)
        params = parse_qs(parsed_url.query)

        def get_param(key, default=''):
            val = params.get(key, [default])
            return val[0] if val else default

        headers = {
            'accept': '*/*',
            'accept-language': 'vi,en;q=0.9',
            'aov-language': 'VN',
            'aov-region': get_param('aov_region', '1137'),
            'areaid': get_param('aov_areaid', '1'),
            'camp-authtype': 'msdk',
            'camp-source': 'AOV-CAMP',
            'content-type': 'application/json',
            'logicworldid': get_param('partition', '1011'),
            'msdk-channelid': get_param('channelid', '10'),
            'msdk-gameid': get_param('gameid', '1137'),
            'msdk-itopencodeparam': get_param('itopencodeparam', '') or get_param('access_token', ''),
            'msdk-os': get_param('os', '1'),
            'origin': 'https://kgvn-camp.mobagarena.com',
            'referer': 'https://kgvn-camp.mobagarena.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.post(USER_INFO_API_URL, headers=headers, json={}, timeout=10)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/change-poster', methods=['POST'])
def change_poster():
    try:
        webview_url = request.form.get('webview_url', '').strip()
        poster_id = request.form.get('poster_id', '7562049').strip()
        custom_encodeparam = request.form.get('encodeparam', '').strip()
        file = request.files.get('file')

        if not webview_url:
            return jsonify({'success': False, 'message': 'Vui lòng cung cấp Link Webview Liên Quân!'}), 400

        if not file:
            return jsonify({'success': False, 'message': 'Vui lòng cung cấp file ảnh!'}), 400

        # Parse query params from webview_url
        parsed_url = urlparse(webview_url)
        params = parse_qs(parsed_url.query)

        def get_param(key, default=''):
            val = params.get(key, [default])
            return val[0] if val else default

        logicworldid = get_param('partition', '1011')
        areaid = get_param('aov_areaid', '1')
        aov_region = get_param('aov_region', '1137')
        channelid = get_param('channelid', '10')
        gameid = get_param('gameid', '1137')
        msdk_os = get_param('os', '1')
        itopencodeparam = get_param('itopencodeparam', '') or get_param('access_token', '')
        encodeparam_from_url = get_param('encodeparam', '')
        
        encodeparam = custom_encodeparam or encodeparam_from_url

        # Build headers
        headers = {
            'accept': '*/*',
            'accept-language': 'vi,en;q=0.9',
            'aov-language': 'VN',
            'aov-region': aov_region,
            'areaid': areaid,
            'camp-authtype': 'msdk',
            'camp-source': 'AOV-CAMP',
            'content-type': 'application/json',
            'logicworldid': logicworldid,
            'msdk-channelid': channelid,
            'msdk-gameid': gameid,
            'msdk-itopencodeparam': itopencodeparam,
            'msdk-os': msdk_os,
            'origin': 'https://kgvn-camp.mobagarena.com',
            'referer': 'https://kgvn-camp.mobagarena.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36'
        }

        # Auto-fetch encodeparam (encryption) if missing
        if not encodeparam:
            try:
                info_res = requests.post(USER_INFO_API_URL, headers=headers, json={}, timeout=10)
                info_data = info_res.json()
                if info_data.get('code') == 0:
                    encodeparam = info_data.get('data', {}).get('encryption', '')
            except Exception as e:
                print("Error auto-fetching encodeparam:", e)

        if encodeparam:
            headers['encodeparam'] = encodeparam

        # Tự động tạo poster mới để lấy posterId chuẩn nhất
        create_poster_url = 'https://kgvn-api.mobagarena.com/api/game/poster/playerimage/createposter'
        try:
            create_res = requests.post(create_poster_url, headers=headers, json={}, timeout=10)
            create_data = create_res.json()
            if create_data.get('code') == 0 and create_data.get('data', {}).get('posterId'):
                poster_id = str(create_data['data']['posterId'])
                print(f"Auto-fetched new posterId: {poster_id}")
        except Exception as e:
            print("Error auto-fetching posterId via createposter:", e)

        try:
            poster_id_int = int(poster_id)
        except ValueError:
            poster_id_int = 7562049


        # 2. Lấy credentials upload từ COS
        cos_cred_url = 'https://kgvn-api.mobagarena.com/api/game/poster/getcoscredential'
        cos_payload = {
            "scene": "PlayerimagePoster",
            "fileName": f"0/1/{poster_id}.png"
        }
        
        try:
            cos_res = requests.post(cos_cred_url, headers=headers, json=cos_payload, timeout=10)
            cos_data = cos_res.json()
            if cos_data.get('code') != 0:
                return jsonify({'success': False, 'message': f"Lỗi lấy COS credential: {cos_data.get('msg')}"}), 400
            
            cred = cos_data['data']
        except Exception as e:
            return jsonify({'success': False, 'message': f"Lỗi kết nối COS credential: {str(e)}"}), 500

        # 3. Upload file lên Tencent COS bằng qcloud_cos
        try:
            from qcloud_cos import CosConfig, CosS3Client
            config = CosConfig(
                Region=cred['region'],
                SecretId=cred['tmpSecretId'],
                SecretKey=cred['tmpSecretKey'],
                Token=cred['token']
            )
            client = CosS3Client(config)
            
            bucket = f"{cred['bucket']}-{cred['appId']}"
            key = cred['path'] # Phải có dấu / ở đầu nếu COS yêu cầu
            file_data = file.read()
            print(f"Uploading file to COS: {len(file_data)} bytes, type: {file.content_type}")
            client.put_object(
                Bucket=bucket,
                Body=file_data,
                Key=key,
                EnableMD5=False,
                ContentType=file.content_type
            )
            
            # Extract base path for saveposter (bỏ phần 0/1/poster_id.png)
            base_path = key.split('0/1/')[0] if '0/1/' in key else key
            pic_url = f"{cred['cdnHost'].rstrip('/')}{base_path}"
            if not pic_url.endswith('/'):
                pic_url += '/'
                
        except Exception as e:
            return jsonify({'success': False, 'message': f"Lỗi khi upload ảnh lên COS: {str(e)}"}), 500

        import time
        time.sleep(5) # Đợi 5s để COS đồng bộ sang CDN trước khi gọi saveposter

        # Payload construction matching Garena's expected structure
        payload = {
            "posterId": str(poster_id_int),
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

        # Send request to Mobagarena API
        response = requests.post(TARGET_API_URL, headers=headers, json=payload, timeout=15)
        
        try:
            res_data = response.json()
        except Exception:
            res_data = {'raw_text': response.text}

        if response.status_code == 200 and res_data.get('code') == 0:
            return jsonify({
                'success': True,
                'message': 'Đã gửi yêu cầu đổi ảnh load trận thành công!',
                'garena_response': res_data
            })
        else:
            return jsonify({
                'success': False,
                'message': f"Lỗi từ Garena: {res_data.get('msg', 'Không rõ lỗi')}",
                'garena_response': res_data
            }), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi hệ thống: {str(e)}'}), 500

if __name__ == '__main__':
    print("Starting AOV Poster Manager server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
