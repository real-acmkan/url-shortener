import os
import smtplib
import settings
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_mail(reset_token, email, mode, logger):
    if mode == "verify":
       reset_link = f"http://{settings.APP_HOST}:{settings.APP_PORT}/auth/verify?token={reset_token}"
    else:
       reset_link = f"http://{settings.APP_HOST}:{settings.APP_PORT}/auth/validate-reset?token={reset_token}"

    sender_email="linkify@unb.ca"
    receiver_email=email
    if mode == "verify":
      subject="Verify your Linkify account"
    else:
      subject="Reset your Linkify password"

    text = f"""
    We received a request to reset your password.

    Click the link below to change your password:
    {reset_link}

    If you didn’t request this, you can safely ignore this email.
    """
    if mode == "verify":
       text = f"""

      Click the link below to verify your account:
      {reset_link}

      """

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
          <h2 style="color: #2d2d2d;">{"Verify your Linkify account" if mode == "verify" else "Reset your Linkify password"}</h2>
          <p style="font-size: 16px; color: #555555;">
           {"Thank you for choosing Linkify. In order to use our service, we require users to have a verified email address." if mode == "verify" else "We received a request to reset your password. If you made this request, click the button below:"}
          </p>
          <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_link}" style="background-color: #007BFF; color: #ffffff; padding: 14px 24px; border-radius: 5px; text-decoration: none; font-size: 16px;">
              {"Verify Account" if mode == "verify" else "Change My Password"}
            </a>
          </div>
          <p style="font-size: 14px; color: #999999;">
            If you didn’t request this, you can safely ignore this email.
          </p>
          <hr style="margin-top: 30px; border: none; border-top: 1px solid #eeeeee;">
          <p style="font-size: 12px; color: #cccccc; text-align: center;">
            © 2025 Linkify Inc. All rights reserved.
          </p>
        </div>
      </body>
    </html>
    """

    try:
        message = MIMEMultipart("alternative")
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(text, "plain"))
        message.attach(MIMEText(html, "html"))

        with smtplib.SMTP("smtp.unb.ca", 25) as server:
            server.send_message(message)

        logger.info("Password reset email sent to %s", email)
        return True
    except Exception as e:
        logger.info("Failed to send reset email: %s", e)
        return False