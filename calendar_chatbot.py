#!/usr/bin/env python3
"""
Calendar Importer Chat Bot
A conversational tool to add or remove events from macOS Calendar.
Supports natural language commands and file processing (PDF, Word, Excel).
"""

"""
README:
# Calendar Importer Chat Bot

A conversational tool to manage events in your macOS Calendar. Interact via natural language commands to add or remove appointments, or process files (PDF, Word, Excel) for bulk event imports.

## Features

- **Natural Language Interaction**: Chat-based interface for adding/removing events.
- **File Processing**: Supports PDF, Word (.docx), and Excel (.xlsx) files for extracting dates and descriptions.
- **Flexible Date Parsing**: Recognizes MM/DD/YYYY and DD-Month formats, with default times.
- **macOS Calendar Integration**: Uses AppleScript to add/remove events from the default "Home" calendar.

## Installation

1. Ensure Python 3.9+ is installed.
2. Install required dependencies:
   ```
   pip install PyPDF2 python-docx openpyxl
   ```

## Usage

Run the script:
```
python3 calendar_importer.py
```

### Examples

- Add an event: `I have an appointment on 04/15/2026 at 10:00 - Meeting with team`
- Remove an event: `The meeting on 04/15/2026 got canceled`
- Process a file: `/path/to/your/schedule.pdf`

Type `exit` or `quit` to end the session.

## How It Works

- **Parsing**: Uses regex to extract dates, times, and descriptions from user input or file text.
- **Actions**: Determines add/remove based on keywords like "appointment", "cancel".
- **Calendar Ops**: Executes AppleScript commands to modify the Calendar app.

## Notes

- Assumes dates are in MM/DD/YYYY or DD-Month (current year).
- Default time is 6:00 AM if not specified.
- Events are added to the "Home" calendar; change in code if needed.
- For file processing, provide the full path.
"""

import re
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from PyPDF2 import PdfReader
except ImportError:
    print("PyPDF2 not installed. Install with: pip install PyPDF2")
    sys.exit(1)

try:
    from docx import Document
except ImportError:
    print("python-docx not installed. Install with: pip install python-docx")
    sys.exit(1)

try:
    import openpyxl
except ImportError:
    print("openpyxl not installed. Install with: pip install openpyxl")
    sys.exit(1)

def extract_text_from_file(file_path):
    """Extract text from PDF, Word, or Excel file."""
    if not os.path.exists(file_path):
        return None
    
    ext = Path(file_path).suffix.lower()
    text = ""
    
    if ext == '.pdf':
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or ""
    elif ext in ['.docx', '.doc']:
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif ext in ['.xlsx', '.xls']:
        wb = openpyxl.load_workbook(file_path)
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                text += " ".join(str(cell) for cell in row if cell) + "\n"
    else:
        return None
    
    return text

def parse_dates_from_text(text):
    """Parse dates and descriptions from text."""
    events = []
    lines = text.split('\n')
    
    # Regex patterns
    pattern_date = re.compile(r'(\d{1,2}/\d{1,2}/\d{4})')
    pattern_month = re.compile(r'(?i)(\d{1,2})-(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)')
    pattern_time = re.compile(r'(\d{1,2}):(\d{2})')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        dates = []
        # Find MM/DD/YYYY
        for match in pattern_date.finditer(line):
            dates.append(match.group(1))
        
        # Find DD-Month
        for match in pattern_month.finditer(line):
            day, month = match.groups()[:2]
            # Convert to MM/DD/YYYY, assume current year
            month_map = {'jan':1, 'feb':2, 'mar':3, 'apr':4, 'may':5, 'jun':6, 'jul':7, 'aug':8, 'sep':9, 'oct':10, 'nov':11, 'dec':12}
            month_num = month_map.get(month.lower()[:3], 1)
            year = datetime.now().year
            date_str = f"{month_num}/{int(day)}/{year}"
            dates.append(date_str)
        
        if dates:
            # Extract time if present
            time_match = pattern_time.search(line)
            time_str = "06:00"  # default
            if time_match:
                time_str = f"{time_match.group(1)}:{time_match.group(2)}"
            
            # Description: remove date and time from line
            desc = re.sub(pattern_date, '', line)
            desc = re.sub(pattern_month, '', desc)
            desc = re.sub(pattern_time, '', desc).strip()
            if not desc:
                desc = "Event"
            
            for date in dates:
                events.append({
                    'date': date,
                    'time': time_str,
                    'description': desc
                })
    
    return events

def create_event(date, time, description):
    """Add event to macOS Calendar using AppleScript."""
    # Combine date and time
    datetime_str = f"{date} {time}"
    dt = datetime.strptime(datetime_str, "%m/%d/%Y %H:%M")
    start_date = dt.strftime("%m/%d/%Y")
    start_time = dt.strftime("%I:%M:%S %p")
    
    script = f'''
    tell application "Calendar"
        tell calendar "Home"
            make new event with properties {{summary:"{description}", start date:date "{start_date} {start_time}", end date:date "{start_date} {start_time}" + 1 * hours}}
        end tell
    end tell
    '''
    
    try:
        subprocess.run(['osascript', '-e', script], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def remove_event(date, time, description):
    """Remove event from macOS Calendar using AppleScript."""
    datetime_str = f"{date} {time}"
    dt = datetime.strptime(datetime_str, "%m/%d/%Y %H:%M")
    start_date = dt.strftime("%m/%d/%Y")
    start_time = dt.strftime("%I:%M:%S %p")
    
    script = f'''
    tell application "Calendar"
        tell calendar "Home"
            set theEvents to (every event whose summary is "{description}" and start date is date "{start_date} {start_time}")
            repeat with anEvent in theEvents
                delete anEvent
            end repeat
        end tell
    end tell
    '''
    
    try:
        subprocess.run(['osascript', '-e', script], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def parse_user_input(user_input):
    """Parse user input to determine action and extract events."""
    input_lower = user_input.lower()
    events = parse_dates_from_text(user_input)
    
    if events:
        # Determine action based on keywords
        if any(word in input_lower for word in ['cancel', 'remove', 'delete', 'canceled']):
            return 'remove', events
        else:
            return 'add', events
    else:
        # Check if it's a file path
        if os.path.isfile(user_input.strip()):
            text = extract_text_from_file(user_input.strip())
            if text:
                events = parse_dates_from_text(text)
                return 'add_file', events
            else:
                return 'error', "Unsupported file or unable to read."
        else:
            return 'unknown', "No dates found. Try saying 'I have an appointment on 04/15/2026' or provide a file path."

def main():
    print("Welcome to Calendar Chat!")
    print("You can say things like:")
    print("- 'I have an appointment on 04/15/2026 at 10:00 - Meeting with team'")
    print("- 'The meeting on 04/15/2026 got canceled'")
    print("- Or just provide a file path like '/path/to/schedule.pdf'")
    print("Type 'exit' to quit.")
    
    while True:
        try:
            user_input = input("> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
            
            action, data = parse_user_input(user_input)
            
            if action == 'add':
                for event in data:
                    if create_event(event['date'], event['time'], event['description']):
                        print(f"Added event: {event['date']} {event['time']} - {event['description']}")
                    else:
                        print(f"Failed to add event: {event['date']} {event['time']} - {event['description']}")
            elif action == 'remove':
                for event in data:
                    if remove_event(event['date'], event['time'], event['description']):
                        print(f"Removed event: {event['date']} {event['time']} - {event['description']}")
                    else:
                        print(f"Failed to remove event: {event['date']} {event['time']} - {event['description']}")
            elif action == 'add_file':
                for event in data:
                    if create_event(event['date'], event['time'], event['description']):
                        print(f"Added event from file: {event['date']} {event['time']} - {event['description']}")
                    else:
                        print(f"Failed to add event from file: {event['date']} {event['time']} - {event['description']}")
            elif action == 'error':
                print(data)
            else:
                print(data)
        
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
