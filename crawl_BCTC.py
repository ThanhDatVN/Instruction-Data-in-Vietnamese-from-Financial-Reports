import os
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- CẤU HÌNH ---
URL_TRANG_WEB = "https://congbothongtin.ssc.gov.vn/faces/NewsSearch?fbclid=IwY2xjawMASyBleHRuA2FlbQIxMABicmlkETF6RzU0dnFhNHNFYkRsenhpAR6xodq6qlHzzAZAiqopSqRj81j5OI0nG5L9JHyhsalprcD1UUxmtE0v7q5HUg_aem_ef83kbnyQZUgrMXnWgS7dA"
DOWNLOAD_FOLDER = r"D:\TaiLieuBCTC"
URL_PATTERN = "[*.]ssc.gov.vn"
LOG_FILE_PATH = os.path.join(DOWNLOAD_FOLDER, "download_log.txt")

# đồng chí dũng
# START_PAGE = 1
# END_PAGE = 231

# đồng chí hoàng bùi
# START_PAGE = 232
# END_PAGE = 463

# đồng chí thành đật
# START_PAGE = 464
# END_PAGE = 695

def create_driver():
    prefs = {
        "download.default_directory": DOWNLOAD_FOLDER,
        "profile.content_settings.exceptions.automatic_downloads": {
            f'{URL_PATTERN},*': {
                'setting': 1,  # 1 = Cho phép (Allow), 2 = Chặn (Block)
                'last_modified': str(int(time.time() * 1000)) # Dấu thời gian, bắt buộc để Chrome chấp nhận
            }
        }
    }    
    chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument("--headless")  # Kích hoạt chế độ chạy ngầm
    # chrome_options.add_argument("--window-size=1920,1080") # Đặt kích thước cửa sổ ảo
    # chrome_options.add_argument("--disable-gpu") # Tăng tính ổn định
    # chrome_options.add_argument("--no-sandbox") # Thường cần thiết khi chạy trên server
    # chrome_options.add_argument("--disable-dev-shm-usage") # Khắc phục lỗi tài nguyên
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=chrome_options,
    )
    driver.maximize_window()
    return driver

# --- CẢI TIẾN: Hàm chờ cho NHIỀU file được tải xong ---
def wait_for_all_downloads_complete(download_folder, num_files_to_expect, timeout_per_file=60):
    """
    Đợi cho đến khi một số lượng file mong đợi được tải xong.
    """
    print(f"   -> Đang chờ {num_files_to_expect} file tải về...")
    files_before = set(os.listdir(download_folder))
    downloaded_files = []
    
    total_timeout = num_files_to_expect * timeout_per_file
    start_time = time.time()

    while len(downloaded_files) < num_files_to_expect:
        # Kiểm tra timeout tổng
        if time.time() - start_time > total_timeout:
            print(f"   -> LỖI: Hết thời gian chờ ({total_timeout}s). Chỉ tải được {len(downloaded_files)}/{num_files_to_expect} file.")
            return downloaded_files

        current_files = set(os.listdir(download_folder))
        new_files = current_files - files_before
        
        # Kiểm tra các file mới xem đã tải xong chưa
        for filename in new_files:
            if not filename.endswith('.crdownload') and filename not in [os.path.basename(p) for p in downloaded_files]:
                try:
                    file_path = os.path.join(download_folder, filename)
                    size_before = os.path.getsize(file_path)
                    time.sleep(1) # Chờ 1 giây để đảm bảo file không còn đang được ghi
                    size_after = os.path.getsize(file_path)

                    if size_before == size_after and size_before > 0:
                        print(f"   -> Đã xong file: {filename}")
                        downloaded_files.append(file_path)
                        # Cập nhật files_before để không kiểm tra lại file này
                        files_before.add(filename)

                except FileNotFoundError:
                    continue
        
        time.sleep(1) # Nghỉ giữa các lần kiểm tra

    print(f"   -> Tải xong toàn bộ {num_files_to_expect} file!")
    return downloaded_files

def load_processed_ids(log_file):
    if not os.path.exists(log_file):
        return set()
    with open(log_file, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f)

def log_processed_ids(log_file, ids_to_log):
    with open(log_file, 'a', encoding='utf-8') as f:
        for unique_id in ids_to_log:
            f.write(unique_id + '\n')

# --- BẮT ĐẦU KỊCH BẢN CHÍNH ---
driver = create_driver()
driver.get(URL_TRANG_WEB)

processed_ids = load_processed_ids(LOG_FILE_PATH)
print(f"Đã tìm thấy {len(processed_ids)} mục đã được xử lý trong các lần chạy trước.")

page_number = 1
total_files_downloaded = len(processed_ids)

if START_PAGE > 1:
    print(f"--- Đang di chuyển đến trang bắt đầu: {START_PAGE} ---")
    while page_number < START_PAGE:
        try:
            wait = WebDriverWait(driver, 20)
            xpath_next_page = "//a[.//img[contains(@src, 'nextitem_ena.png')]]"
            next_page_button = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_next_page)))
            driver.execute_script("arguments[0].click();", next_page_button)
            page_number += 1
            print(f"Đã chuyển đến trang {page_number}...")
            time.sleep(3) # Chờ trang tải
        except TimeoutException:
            print(f"Lỗi: Không thể tìm thấy nút 'Next Page' khi đang ở trang {page_number}. Có thể trang cuối cùng nhỏ hơn trang bắt đầu của bạn.")
            driver.quit()
            exit()
    print(f"--- Đã đến trang bắt đầu. Bắt đầu quá trình tải ---")

while page_number <= END_PAGE:
    print(f"\n--- BẮT ĐẦU XỬ LÝ TRANG {page_number} ---")
    try:
        xpath_locator = "//a[.//img[contains(@src, '/image/icons/download.png')]]"
        wait = WebDriverWait(driver, 10)
        all_buttons = wait.until(EC.presence_of_all_elements_located((By.XPATH, xpath_locator)))
        
        # --- CẢI TIẾN: Logic tải hàng loạt ---
        ids_on_page = [button.get_attribute('id') for button in all_buttons]
        ids_to_download = [uid for uid in ids_on_page if uid and uid not in processed_ids]
        
        if not ids_to_download:
            print("Tất cả các mục trên trang này đã được tải. Chuyển trang tiếp theo.")
        else:
            print(f"Tìm thấy {len(ids_to_download)} mục mới cần tải trên trang này.")
            
            # 1. Click liên tục vào các nút cần tải
            for uid in ids_to_download:
                try:
                    print(f"  -> Bắt đầu tải mục ID: {uid}")
                    # Dùng find_element để lấy nút mới nhất và click
                    button_to_click = driver.find_element(By.ID, uid)
                    driver.execute_script("arguments[0].click();", button_to_click)
                    time.sleep(0.2) # Thêm một khoảng nghỉ nhỏ giữa các lần click để tránh làm trình duyệt bị quá tải
                except Exception as e:
                    print(f"  -> Lỗi khi click vào nút ID {uid}: {e}")
            
            # 2. Chờ cho tất cả file được tải xong
            downloaded_files = wait_for_all_downloads_complete(DOWNLOAD_FOLDER, len(ids_to_download), timeout_per_file=120)
            
            # 3. Ghi log cho tất cả các ID đã được yêu cầu tải
            if downloaded_files:
                log_processed_ids(LOG_FILE_PATH, ids_to_download)
                processed_ids.update(ids_to_download)
                total_files_downloaded += len(downloaded_files)
                print(f"   -> Đã ghi nhận {len(ids_to_download)} ID vào log.")
    
    except Exception as e:
        print(f"Lỗi nghiêm trọng trong quá trình xử lý trang {page_number}: {e}")
        continue
    print(f"\nĐã tải được {total_files_downloaded} file.")
    if page_number == END_PAGE:
        print(f"Đã hoàn thành công việc được giao (đến trang {END_PAGE}). Dừng lại.")
        break
    # --- Logic chuyển trang (giữ nguyên) ---
    print("\nTìm kiếm nút 'Next Page'...")
    try:
        wait = WebDriverWait(driver, 5)
        xpath_next_page = "//a[.//img[contains(@src, 'nextitem_ena.png')]]"
        next_page_button = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_next_page)))
        
        print("Đã tìm thấy nút 'Next Page'. Chuyển trang...")
        driver.execute_script("arguments[0].click();", next_page_button)
        time.sleep(5)
        page_number += 1
    except TimeoutException:
        print("Không tìm thấy nút 'Next Page' hoặc đã ở trang cuối cùng.")
        break

print("="*50)
driver.quit()