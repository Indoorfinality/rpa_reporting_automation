import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    #Credentials
    login_url: str = os.getenv("LOGIN_URL")
    username: str  = os.getenv("APP_USERNAME")
    password: str  = os.getenv("APP_PASSWORD")

    #Browser settings
    headless: bool = os.getenv("HEADLESS", "false").lower() == "true"
    slow_mo: int   = int(os.getenv("SLOW_MO", "150"))
    timeout: int   = int(os.getenv("TIMEOUT", "30000"))

    #LOGIN PAGE SELECTORS
    sel_username: str     = 'input#userid'
    sel_password: str     = 'input#TypeName'
    sel_login_btn: str    = 'button#add'


    #DASHBOARD PAGE SELECTORS
    sel_home_link: str    = 'a[href="/Dashboard.aspx"]'  # Primary selector (link)
    sel_home_btn: str     = 'span.glyphicon-home'  # Fallback selector (icon span)

    #HOME PAGE
    home_url: str         = "http://172.16.0.37:805/Home.aspx"
    sel_logged_in: str    = 'h4:has-text("Welcome To Social Security Fund")' 
    
    #RE Framework
    max_retries: int = 3

    #Output
    output_dir: str = "output"

    #Master template
    master_template: str = os.getenv("MASTER_TEMPLATE", "Master.xlsx")

    popup_recovery_ms: int = 5000
