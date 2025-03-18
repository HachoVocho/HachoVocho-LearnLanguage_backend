import requests


def send_otp_via_google_script(email, otp):
    url = "https://script.google.com/macros/s/AKfycbzLBixWfy-uegOrgPRrSLH6PacXwCal51yBHG2yQDYd3T3M7lGJ4wH9WOVG2pgVPFk0gA/exec"
    data = {
        "email": email,
        "otp": otp,
    }
    response = requests.post(url, json=data)
    print(response.content)
    return response.json()

send_otp_via_google_script("dholujustchill2@gmail.com",'123456')