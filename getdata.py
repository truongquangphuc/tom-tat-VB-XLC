import requests, os
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv, set_key

# Tải các biến môi trường từ file .env
load_dotenv()
# URL và headers chung
BASE_URL = 'https://vpdt.angiang.gov.vn'
API_URL = 'https://angiang-api.vnptioffice.vn/api'
HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8,af;q=0.7,sv;q=0.6',
    'Content-Type': 'application/x-www-form-urlencoded',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0',
}

# Lấy refresh_token từ biến môi trường
refresh_token = st.secrets["REFRESH_TOKEN"]

class ApiClient:
    def __init__(self, username, password):
        self.session = requests.Session()
        self.username = username
        self.password = password
        self.access_token = None
        self.login()

    def get_soup(self, url):
        """Lấy HTML từ URL và trả về đối tượng BeautifulSoup."""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            raise SystemExit(f"HTTP Request failed: {e}")

    def login(self):
        """Đăng nhập và lấy access token."""
        soup = self.get_soup(BASE_URL)
        form_data = {input.get('name'): input.get('value') for input in soup.find_all('input', type='hidden')}
        form_data.update({'Username': self.username, 'Password': self.password})
        
        try:
            login_response = self.session.post(BASE_URL, data=form_data)
            login_response.raise_for_status()
            if not login_response.ok:
                raise Exception("Đăng nhập thất bại!")
            
            token_data = self.get_access_token(refresh_token=refresh_token)
            if not token_data.get('success'):
                raise Exception(f"Lấy access token không thành công! Thông báo: {token_data.get('message')}")
            
            self.access_token = token_data['data'].get('access_token')
            HEADERS['Authorization'] = f'Bearer {self.access_token}'
        except requests.RequestException as e:
            raise SystemExit(f"Login request failed: {e}")

    def get_access_token(self, refresh_token):
        """Lấy access token từ refresh token và cập nhật refresh token mới."""
        url = f'{API_URL}/can-bo/access-token?refresh_token={refresh_token}'
        try:
            response = self.session.get(url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
            
            # Cập nhật refresh_token nếu có giá trị mới và lưu vào .env
            #new_refresh_token = data.get('data', {}).get('refresh_token')
            #if new_refresh_token and new_refresh_token != refresh_token:
                #self.update_refresh_token(new_refresh_token)
            
            return data
        except requests.RequestException as e:
            raise SystemExit(f"Access token request failed: {e}")

    def update_refresh_token(self, new_refresh_token):
        """Cập nhật giá trị refresh_token trong file .env."""
        env_path = '.env'  # Đường dẫn tới file .env
        set_key(env_path, 'REFRESH_TOKEN', new_refresh_token)
        print(f"Refresh token đã được cập nhật thành công trong file .env: {new_refresh_token}")


    def fetch_data(self, url, data=None, params=None, method='GET'):
        """Gửi yêu cầu và trả về dữ liệu từ API."""
        method_function = self.session.post if method.upper() == 'POST' else self.session.get
        try:
            response = method_function(url, headers=HEADERS, data=data, params=params)
            response.raise_for_status()
            
            # In ra mã trạng thái và nội dung phản hồi
            # print(f"Status Code: {response.status_code}")
            # print(f"Raw response content: {response.text}")

            # Kiểm tra nếu phản hồi có kiểu JSON
            try:
                return response.json()
            except ValueError:
                # Nếu không thể phân tích thành JSON, trả về văn bản
                return response.text
        except requests.RequestException as e:
            raise SystemExit(f"API request failed: {e}")

    def tra_cuu_van_ban(self, search_params):
        """Tra cứu văn bản và trả về danh sách văn bản chi tiết."""
        search_data = self.fetch_data(
            f'{API_URL}/van-ban/tra-cuu-van-ban-di-agg', 
            data=search_params, 
            method='POST'
        )
        van_ban_ma = [str(int(item.get('ma_van_ban', 0))) for item in search_data.get('data', [])]

        details_list = []
        for ma_van_ban in van_ban_ma:
            detail_data = self.fetch_data(
                f'{API_URL}/van-ban-di/chi-tiet-van-ban-di', 
                params={'ma_van_ban_di': ma_van_ban, 'ma_ctcb': '2195'}
            )
            details_list.append(detail_data.get('data', {}))
        
        return details_list

    def thong_tin_can_bo(self):
        """Lấy thông tin cán bộ dựa trên tên đăng nhập và mật khẩu."""
        json_data = self.fetch_data(
            f'{API_URL}/can-bo/danh-sach-cong-tac-can-bo', 
            data={'password': self.password, 'username': self.username},
            method='POST'
        )
        if json_data.get("success"):
            return json_data["data"]
        return {"error": f"Lỗi: {json_data.get('message')}"}

    def danh_sach_van_ban_den(self, ma_ctcb_kc, ho_va_ten_can_bo, ma_don_vi_cha):
        """Lấy danh sách văn bản đến dựa trên các thông số đầu vào."""
        current_year = datetime.now().year
        nhan_den_ngay = f'31/12/{current_year}'
        nhan_tu_ngay = f'01/01/{current_year}'
        
        data = {
            'co_tep_tin': '-1',
            'ma_can_bo': str(ma_ctcb_kc),
            'ma_don_vi_quan_tri': ma_don_vi_cha,
            'ma_loai_ttdh': '0',
            'ma_yeu_cau': '2',
            'nam': str(current_year),
            'nhan_den_ngay': nhan_den_ngay,
            'nhan_tu_ngay': nhan_tu_ngay,
            'page': '1',
            'size': '20',
            'trang_thai_ttdh_gui': '-1',
            'trang_thai_xu_ly': '1',
        }

        response = self.fetch_data(
            'https://angiang-api.vnptioffice.vn/api/van-ban-den/danh-sach-van-ban-den-theo-trang-thai-cua-chuyen-vien',
            data=data,
            method='POST'
        )
        
        if response.get("success"):
            data_list = [item for item in response.get("data", []) if item.get('nguoi_xu_ly_chinh') and ho_va_ten_can_bo in item['nguoi_xu_ly_chinh']]
            sorted_data = sorted(data_list, key=lambda x: x.get('ngay_den', ''), reverse=True)
            return sorted_data
        else:
            return {"error": f"Lỗi: {response.get('message')}"}

def file_name(path):
    """Trích xuất tên tệp từ đường dẫn."""
    path = str(path)
    parts = path.split('__')
    last_part = parts[-1]
    index = 0
    if 'am' in last_part:
        index = last_part.index('am') + 3
    if 'pm' in last_part:
        index = last_part.index('pm') + 3
    return last_part[index:]

def file_url(path, type):
    """Tạo URL tải hoặc xem tệp."""
    type_rs = '/download/' if type == 'download' else '/view/'
    try:
        file_name_part = file_name(path)
        parts = path.split('___')
        temp = parts[1].split('__')
        url = temp[0]
        if 'http-' in url or 'https-' in url:
            url = url.replace('https-', 'https://').replace('http-', 'http://')
        else:
            url = url.replace('https', 'https://').replace('http', 'http://')

        url = url.replace('localhost', 'localhost:')
        url += '/api/file-manage/read-file/'
        url += path + type_rs
        url += refresh_token
        url += '/' + file_name_part
    except Exception as e:
        print(f"Error constructing URL: {e}")
        return ''
    return url
