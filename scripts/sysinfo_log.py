import os
import shutil
import time
import re
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

LOG_DIR = os.path.expanduser('~/work/logs')
LOG_PATH = os.path.join(LOG_DIR, 'sysinfo.csv')

# 로그 저장 폴더가 없으면 자동 생성
os.makedirs(LOG_DIR, exist_ok=True)

def cpu_temp():
    with open('/sys/class/thermal/thermal_zone0/temp') as f:
        return int(f.read()) / 1000

def mem_available_gb():
    """/proc/meminfo에서 MemAvailable 값을 읽어 GB 단위로 반환합니다."""
    with open('/proc/meminfo') as f:
        for line in f:
            if 'MemAvailable' in line:
                # 숫자 부분만 추출 (예: 1234567 kB -> 1234567)
                kb = int(re.search(r'\d+', line).group())
                return kb / (1024 ** 2)  # kB -> GB 변환
    return 0.0

# 10MB(10 * 1024 * 1024 바이트) 크기 제한 핸들러 설정
# 파일이 10MB를 넘으면 기존 파일은 sysinfo.csv.1로 바뀌고 새 sysinfo.csv가 생성됩니다.
handler = RotatingFileHandler(LOG_PATH, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8')
logger = logging.getLogger("SysInfoLogger")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# 새 파일이거나 크기가 0일 때 CSV 헤더(타이틀) 작성
if not os.path.exists(LOG_PATH) or os.path.getsize(LOG_PATH) == 0:
    logger.info('time,temp_c,disk_free_gb,mem_available_gb')

while True:
    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        temp = f"{cpu_temp():.1f}"
        disk = f"{shutil.disk_usage('/').free / 1024**3:.1f}"
        mem = f"{mem_available_gb():.1f}"
        
        # CSV 형식으로 한 줄 작성 (RotatingFileHandler가 자동으로 flush를 처리함)
        logger.info(f"{current_time},{temp},{disk},{mem}")
        
    except Exception as e:
        print(f"에러 발생: {e}")
        
    time.sleep(1)
