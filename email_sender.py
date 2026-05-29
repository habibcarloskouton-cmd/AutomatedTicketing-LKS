import io
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from locars_config import EmailConfig

class EmailSender:
    """Gestion de l'envoi d'emails avec pièces jointes"""

    def __init__(self, config: EmailConfig):
        self.config = config

    def send_ticket(self, recipient_email: str, participant_name: str,
                    ticket_buffer: io.BytesIO, ticket_filename: str,
                    event_name: str) -> tuple[bool, str]:
        try:
            if not self.config.is_valid:
                return False, "Configuration email incomplète"

            msg = MIMEMultipart()
            msg['From'] = self.config.sender
            msg['To'] = recipient_email
            msg['Subject'] = f"Votre billet pour {event_name}"

            body = (
                f"Bonjour {participant_name},\n\n"
                f"Voici votre billet pour l'événement {event_name}.\n"
                f"Merci de présenter le QR Code à l'entrée.\n\n"
                f"Cordialement,\nL'équipe d'organisation."
            )
            msg.attach(MIMEText(body, 'plain'))

            ticket_buffer.seek(0)
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(ticket_buffer.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={ticket_filename}")
            msg.attach(part)

            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.sender, self.config.password)
                server.sendmail(self.config.sender, recipient_email, msg.as_string())

            return True, "Succès"

        except smtplib.SMTPAuthenticationError:
            return False, "Échec d'authentification. Vérifiez votre mot de passe d'application."
        except smtplib.SMTPException as e:
            return False, f"Erreur SMTP: {str(e)}"
        except Exception as e:
            return False, f"Erreur: {type(e).__name__}: {str(e)}"
