import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import re

# 1. THE DATA (Your Crontab)
crontab_text = """
18 02 * * 1-5 . ~/.bashrc; ~/quod/script/qstart all
19 02 * * 1-5 . ~/.bashrc; /opt/quod/scripts/manageELK_xpack_logstash 5
05 01 * * 1-5 . ~/.bashrc; ~/quod/script/qstart FHIDCREF
10 01 * * 1-5 . ~/.bashrc; ~/quod/script/qstart FHIDCDELAYREF
13 01 * * 1-5 . ~/.bashrc; $GIT_FILES/specificConfigs/script/HolidayCalendar.sh
15 01 * * 1-5 . ~/.bashrc; $GIT_FILES/specificConfigs/script/Dictionaryprocess.sh
17 01 * * 1-5 . ~/.bashrc; ~/quod/script/qstart itkoffline
30 01 * * 1-5 . ~/.bashrc; ~/quod/script/qstart ITKHOLIDAYCALENDAR
35 01 * * 1-5 . ~/.bashrc; python3.11 $GIT_FILES/specificConfigs/script/BLMRefData/Quad-BLPMarketlistRequest.py > $LOG_DIR/BLM_COMPOSITE.log
36 01 * * 1-5 . ~/.bashrc; python3.11 $GIT_FILES/specificConfigs/script/BLMRefData/Quad-BLPOMSrefdataRequest.py REFDATA >> $LOG_DIR/BLM_COMPOSITE.log
46 01 * * 1-5 . ~/.bashrc; ~/quod/script/qstart ITKBLMDATA
15 02 * * 1-5 . ~/.bashrc; ~/quod/script/qstop all
12 02 * * 1-5 . ~/.bashrc; $GIT_FILES/specificConfigs/script/updateRefData.sh > $LOG_DIR/updateRefData.log
53 01 * * 1-5 . ~/.bashrc; python3 /opt/quod/support.scripts/BOD/itk_checker.py ITKHOLIDAYCALENDAR
31 02 * * 1-5 . ~/.bashrc; python3 /opt/quod/support.scripts/BOD/itk_checker.py ITKICEDATA
32 02 * * 1-5 . ~/.bashrc; python3 /opt/quod/support.scripts/BOD/itk_checker.py ITKBLMDATA
30 02 * * 1-5 . ~/.bashrc; ~/quod/script/qstart fix1
50 03 * * 1-5 . ~/.bashrc; ~/quod/script/qstart fix2
31 02 * * 1-5 . ~/.bashrc; ~/quod/script/qstart FHIDC
35 02 * * 1-5 . ~/.bashrc; ~/quod/script/qstart FHIDCDELAY
00 09 * * 1-5 . ~/.bashrc; $GIT_FILES/specificConfigs/script/processOnlineRefData.sh > /dev/null 2>&1 &
11 5 * * 1-5 . ~/.bashrc; ~/quod/script/qstart ITKCROSSRATEONLINE
30 23 * * 1-5 . ~/.bashrc;  $GIT_FILES/specificConfigs/script/EODOrder_TOMS.sh >> $LOG_DIR/EODReports.log
31 23 * * 1-5 . ~/.bashrc;  $GIT_FILES/specificConfigs/script/EODExecution_TOMS.sh >> $LOG_DIR/EODReports.log
32 23 * * 1-5 . ~/.bashrc;  $GIT_FILES/specificConfigs/script/EODAllocation_TOMS.sh >> $LOG_DIR/EODReports.log
00 21 * * 1-5 . ~/.bashrc;  $GIT_FILES/specificConfigs/script/EODWafa-Allocation_TOMS.sh >> $LOG_DIR/EODReports.log
03 01 * * * . ~/.bashrc; $GIT_FILES/specificConfigs/script/db_endOfDay_DOR-11627 N 1 N >> $LOG_DIR/db_endOfDay.log
"""

def parse_cron_to_geneos(line):
    # Regex to extract cron parts
    pattern = r'^([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+(.*)$'
    match = re.match(pattern, line.strip())
    if not match: return None
    
    m, h, dom, mon, dow, cmd = match.groups()

    # 1. Determine Component (Logic based on your spreadsheet examples)
    comp = "TOMS"
    clean_cmd = cmd.lower()
    if "fix" in clean_cmd: comp = "TOMS.FIX"
    elif "fh" in clean_cmd or "feed" in clean_cmd: comp = "TOMS.FH"
    elif "itk" in clean_cmd or "refdata" in clean_cmd: comp = "ITK"
    elif "eod" in clean_cmd or "db_endofday" in clean_cmd: comp = "EOD"
    elif "elk" in clean_cmd or "logstash" in clean_cmd: comp = "ELK"

    # 2. Determine Description
    # Extract the script name or the argument after qstart/qstop
    desc = cmd.split("/")[-1].replace(".sh", "").replace(".py", "").strip()
    if "qstart" in cmd or "qstop" in cmd:
        desc = cmd.split("script/")[-1].strip()

    # 3. Monitoring Time (HH:MM)
    # Handle "*" or intervals if they exist, otherwise format HH:MM
    try:
        time_str = f"{h.zfill(2)}:{m.zfill(2)}"
    except:
        time_str = f"{h}:{m}"

    # 4. Days
    days = "Mon-Fri" if dow == "1-5" else "Daily" if dow == "*" else "Sun-Thu" if dow == "0-4" else dow

    return [comp, desc, time_str, days]

def generate_xlsx():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "geneos sheet"

    # Header Row
    headers = ["Component", "Description", "Monitoring Time", "Days"]
    ws.append(headers)

    # Styles (Matching the provided Google Sheet Look)
    header_font = Font(bold=True, size=11)
    header_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid") # Greyish header
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                         top=Side(style='thin'), bottom=Side(style='thin'))

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin_border

    # Parse and fill data
    for line in crontab_text.strip().split('\n'):
        if line.strip() and not line.strip().startswith("#"):
            row_data = parse_cron_to_geneos(line)
            if row_data:
                ws.append(row_data)
                # Apply borders to the new row
                for cell in ws[ws.max_row]:
                    cell.border = thin_border
                    cell.alignment = Alignment(horizontal="left")

    # Column Widths
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 60
    ws.column_dimensions['C'].width = 18
    ws.column_dimensions['D'].width = 12

    filename = "Component_Monitoring_Times.xlsx"
    wb.save(filename)
    print(f"File saved successfully as: {filename}")

if __name__ == "__main__":
    generate_xlsx()