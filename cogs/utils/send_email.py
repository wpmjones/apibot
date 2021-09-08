import smtplib
import ssl

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings

port = 465
email = settings['email']['address']
password = settings['email']['password']

# Create SSL connection
context = ssl.create_default_context()


class SendMail:
    """Send email from bot.hogrider@gmail.com"""
    def __init__(self, recipient_email, recipient_name, bot_name, guild_id, channel_id, message_id):
        self.sender = email
        self.recipient_name = recipient_name
        self.recipient_email = recipient_email
        self.bot_name = bot_name
        self.message_link = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

    def send_mail_down(self):
        with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
            server.login(email, password)

            message = MIMEMultipart("alternative")
            message["Subject"] = f"{self.bot_name} is down!"
            message["From"] = self.sender
            message["To"] = self.recipient_email

            text = f"It would appear that {self.bot_name} is down. Check it out and see what's up!"
            html = (f"<html><body>"
                    f"<p>Greetings!<br>"
                    f"<br>"
                    f"It would appear that {self.bot_name} is down. <a href='{self.message_link}'>Click here</a> "
                    f"to view this notification in Discord. "
                    f"But I promise, it contains less information than this email.<br>"
                    f"<br>"
                    f"Sincerely,<br>"
                    f"Hog Rider<br>"
                    f"<img src='http://www.mayodev.com/images/bothogrider.png'>"
                    f"</p>"
                    f"</body></html>")
            # Convert to MIME format
            part1 = MIMEText(text, "plain")
            part2 = MIMEText(html, "html")
            message.attach(part1)
            message.attach(part2)
            server.sendmail(self.sender, self.recipient_email, message.as_string())

    def send_mail_up(self, downtime):
        with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
            server.login(email, password)

            message = MIMEMultipart("alternative")
            message["Subject"] = f"{self.bot_name} is back up!"
            message["From"] = self.sender
            message["To"] = self.recipient_email

            text = f"{self.bot_name} is back up and online. Downtime: {downtime}"
            html = (f"<html><body>"
                    f"<p>Greetings!</p>"
                    f"<p>{self.bot_name} is now back online. It looks like it was offline for {downtime}.</p>"
                    f"<p>Sincerely,<br>"
                    f"Hog Rider<br>"
                    f"<img src='http://www.mayodev.com/images/bothogrider.png'>"
                    f"</p>"
                    f"</body></html>")
            # Convert to MIME format
            part1 = MIMEText(text, "plain")
            part2 = MIMEText(html, "html")
            message.attach(part1)
            message.attach(part2)
            server.sendmail(self.sender, self.recipient_email, message.as_string())

    def send_mail_followup(self, downtime):
        with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
            server.login(email, password)

            message = MIMEMultipart("alternative")
            message["Subject"] = f"{self.bot_name} is still down!"
            message["From"] = self.sender
            message["To"] = self.recipient_email

            text = f"{self.bot_name} is still offline. Downtime: {downtime}"
            html = (f"<html><body>"
                    f"<p>Greetings!</p>"
                    f"<p>{self.bot_name} is still showing as offline. It looks like it has been offline "
                    f"for {downtime}.</p>"
                    f"<p>Sincerely,<br>"
                    f"Hog Rider<br>"
                    f"<img src='http://www.mayodev.com/images/bothogrider.png'>"
                    f"</p>"
                    f"</body></html>")
            # Convert to MIME format
            part1 = MIMEText(text, "plain")
            part2 = MIMEText(html, "html")
            message.attach(part1)
            message.attach(part2)
            server.sendmail(self.sender, self.recipient_email, message.as_string())
