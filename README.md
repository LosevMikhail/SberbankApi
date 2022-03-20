# Introduction
The API of Sberbank is private. It has been reverse-engineered by decompiling the official client apk, certificate substitution, pinning disabling and performing man-in-the middle with Charles proxy.

# Summary
This API is a part of a P2P trading bot for Binance which is a private project protected by NDA. This is the only part of the project that I may provide.

# Usage
* Use Registration class to obtain a pair of (m_guid, pin). It's gonna need you to provide your login and enter the SMS verification code sent by the bank.
* Use (m_guid, pin) to log in with SberApi (or use LoggerIn to obtain JWT and feet it to SberApi).
* Use its methods to obtain operations
history or transfer money form a card. Obtaining your cards list is not implemented yet.
