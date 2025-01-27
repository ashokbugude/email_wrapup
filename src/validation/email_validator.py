import re
import dns.resolver
import asyncio
from typing import List
import logging

class EmailValidator:
    def __init__(self):
        self.throwaway_domains = {
            'tempmail.com', 'throwawaymail.com', 'temp-mail.org',
            'guerrillamail.com', '10minutemail.com', 'mailinator.com'
            # Add more throwaway domains as needed
        }
        self.logger = logging.getLogger(__name__)
        
    async def is_valid_email(self, email: str) -> bool:
        """
        Validate an email address by checking format, domain blacklist, and MX records.
        
        Args:
            email: The email address to validate
            
        Returns:
            bool: True if email is valid, False otherwise
        """
        try:
            if not isinstance(email, str) or not email:  # Add empty string check
                return False
                
            email = email.strip().lower()  # Normalize email
                
            if not self._check_format(email):
                self.logger.debug(f"Invalid email format: {email}")
                return False
                
            domain = email.split('@')[1]
            if domain.lower() in self.throwaway_domains:  # Case-insensitive domain check
                self.logger.debug(f"Throwaway domain detected: {domain}")
                return False
                
            return await self._check_mx_record(domain)
        except Exception as e:
            self.logger.error(f"Error validating email {email}: {str(e)}")
            return False
        
    def _check_format(self, email: str) -> bool:
        """Validate email format using regex pattern."""
        # More comprehensive regex pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
        
    async def _check_mx_record(self, domain: str) -> bool:
        """Check if domain has valid MX records."""
        try:
            # Remove explicit event loop handling as it's not needed
            await asyncio.get_running_loop().run_in_executor(None, dns.resolver.resolve, domain, 'MX')
            return True
        except dns.resolver.NXDOMAIN:
            self.logger.debug(f"Domain does not exist: {domain}")
            return False
        except (dns.resolver.NoAnswer, dns.resolver.NoNameservers):  # Add NoNameservers exception
            self.logger.debug(f"No MX records found for domain: {domain}")
            return False
        except dns.resolver.Timeout:
            self.logger.warning(f"DNS timeout for domain: {domain}")
            return False
        except Exception as e:
            self.logger.error(f"Error checking MX record for {domain}: {str(e)}")
            return False 