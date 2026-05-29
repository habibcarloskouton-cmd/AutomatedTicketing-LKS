import os
from dataclasses import dataclass

@dataclass
class EmailConfig:
    sender: str = ""
    password: str = ""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587

    @property
    def is_valid(self) -> bool:
        return bool(self.sender and self.password)

DEFAULT_EMAIL_CONFIG = EmailConfig(
    sender=os.getenv("TICKET_EMAIL", "habibcarloskouton@gmail.com"),
    password=os.getenv("TICKET_EMAIL_PASS", "")
)
