# \# Zenithra.ai — Backend v2

# 

# Zenithra.ai is an AI-powered coding assistant backend built with FastAPI and Gemini. Version 2 introduces production-oriented features such as request retries, rate limiting, request logging, user history, personalization, automatic language detection, and conversation context.

# 

# \## Features

# 

# | Feature                          | Description                                                                                                                      |

# | -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |

# | \*\*Retry Logic\*\*                  | Automatically retries Gemini API requests up to 2 times when server errors or timeouts occur, with 1-second and 2-second delays. |

# | \*\*Rate Limiting\*\*                | Limits each IP address to a maximum of 10 requests per minute to reduce spam and abuse.                                          |

# | \*\*Request Logging\*\*              | Records requests in the console and in the `zenithra.log` file.                                                                  |

# | \*\*User History\*\*                 | Stores user questions and answers in a SQLite database (`zenithra.db`).                                                          |

# | \*\*Personalization\*\*              | Detects the user's most frequently used programming language and uses it for future `auto` requests.                             |

# | \*\*Automatic Language Detection\*\* | When `type: "auto"` is provided, the backend detects the programming language from the question and user history.                |

# | \*\*Conversation Context\*\*         | Remembers the previous 3 question-and-answer pairs to provide better answers to follow-up questions.                             |

# | \*\*Response Time\*\*                | Returns the processing time for every response.                                                                                  |

# 

# \## Project Setup

# 

# \### 1. Create a Virtual Environment

# 

# Open a terminal in the backend directory:

# 

# ```bash

# cd backend

# python -m venv venv

# ```

# 

# Activate the virtual environment on Windows:

# 

# ```bash

# venv\\Scripts\\activate

# ```

# 

# \### 2. Install Dependencies

# 

# Install the required Python packages:

# 

# ```bash

# pip install -r requirements.txt

# ```

# 

# SQLite is included with Python, so no separate SQLite installation is required.

# 

# \### 3. Configure the Gemini API Key

# 

# Create a `.env` file from the provided example:

# 

# ```bash

# cp .env.example .env

# ```

# 

# On Windows PowerShell, you can also use:

# 

# ```powershell

# Copy-Item .env.example .env

# ```

# 

# Then open `.env` and add your Gemini API key.

# 

# \*\*Never commit your `.env` file or API keys to GitHub.\*\*

# 

# \### 4. Start the Backend

# 

# Run the FastAPI application using Uvicorn:

# 

# ```bash

# uvicorn main:app --reload

# ```

# 

# The backend will be available at:

# 

# ```text

# http://127.0.0.1:8000

# ```

# 

# \## Request Format

# 

# Each request should include a `user\_id` so that individual user history can be tracked.

# 

# Example:

# 

# ```json

# {

# &#x20; "user\_id": "anil123",

# &#x20; "question": "Reverse a linked list",

# &#x20; "type": "auto"

# }

# ```

# 

# \### Automatic Language Detection

# 

# When:

# 

# ```json

# "type": "auto"

# ```

# 

# is used, the backend automatically determines whether the question is related to Python, C, C++, LeetCode, or another supported category based on the question and the user's previous history.

# 

# \## Response Format

# 

# Example response:

# 

# ```json

# {

# &#x20; "best\_answer": "...(code/answer)...",

# &#x20; "best\_source": "gemini",

# &#x20; "detected\_type": "python",

# &#x20; "response\_time\_ms": 842.5,

# &#x20; "history\_count": 3

# }

# ```

# 

# \### Response Fields

# 

# | Field              | Description                                                   |

# | ------------------ | ------------------------------------------------------------- |

# | `best\_answer`      | The generated coding answer or solution.                      |

# | `best\_source`      | The AI source used to generate the response.                  |

# | `detected\_type`    | The programming language or category detected by the backend. |

# | `response\_time\_ms` | Response processing time in milliseconds.                     |

# | `history\_count`    | Number of previous requests stored for the user.              |

# 

# \## User History

# 

# Zenithra.ai provides a history endpoint:

# 

# ```text

# GET /history/{user\_id}

# ```

# 

# Example:

# 

# ```text

# http://127.0.0.1:8000/history/anil123

# ```

# 

# The endpoint returns the user's previous questions and answers in JSON format.

# 

# \## Rate Limiting

# 

# The backend allows a maximum of \*\*10 requests per minute per IP address\*\*.

# 

# If more than 10 requests are sent within one minute, the API returns an error similar to:

# 

# ```json

# {

# &#x20; "detail": "Too many requests. Maximum 10 requests per minute are allowed."

# }

# ```

# 

# This is expected behavior. Wait for the rate-limit window to reset and try again.

# 

# \## Logging

# 

# The backend creates a `zenithra.log` file in the application directory.

# 

# Example log entry:

# 

# ```text

# 2026-09-03 12:30:15 | INFO | user=anil123 type=python time=842.5ms question='Reverse a linked list'

# ```

# 

# The log contains information such as:

# 

# \* User ID

# \* Detected request type

# \* Processing time

# \* User question

# 

# \## Database

# 

# Zenithra.ai uses SQLite to store user conversation history.

# 

# The database file:

# 

# ```text

# zenithra.db

# ```

# 

# is automatically created when the backend starts and the database is initialized.

# 

# If you want to reset the local database during development, you can delete the `zenithra.db` file and restart the server. A new database will be created automatically.

# 

# > \*\*Production Note:\*\* For a production deployment with multiple users and multiple backend instances, consider migrating from SQLite to PostgreSQL or another production-grade database.

# 

# \## Authentication

# 

# The current version uses a simple text-based `user\_id` for tracking user history.

# 

# There is currently \*\*no real authentication system\*\* such as:

# 

# \* User registration

# \* Login

# \* Password authentication

# \* JWT authentication

# \* OAuth

# 

# This setup is suitable for development, testing, and learning.

# 

# For a production application, implement a proper authentication and authorization system before exposing user-specific data publicly.

# 

# \## API Documentation

# 

# Because the backend uses FastAPI, interactive API documentation is automatically available when the server is running.

# 

# \### Swagger UI

# 

# ```text

# http://127.0.0.1:8000/docs

# ```

# 

# \### ReDoc

# 

# ```text

# http://127.0.0.1:8000/redoc

# ```

# 

# These interfaces can be used to test and explore the available API endpoints.

# 

# \## Project Structure

# 

# ```text

# zenithra.ai/

# │

# ├── backend/

# │   ├── .env.example

# │   ├── README.md

# │   ├── main.py

# │   ├── requirements.txt

# │   └── zenithra.db

# │

# └── frontend/

# &#x20;   ├── index.html

# &#x20;   └── styles.css

# ```

# 

# > \*\*Security:\*\* The local `zenithra.db` file should not be committed to GitHub if it contains real user data. The `.env` file and API credentials should also never be committed.

# 

# \## Future Improvements

# 

# \* Build a complete frontend for the `/solve` and `/history` endpoints.

# \* Add user registration and authentication.

# \* Add JWT-based authorization.

# \* Migrate the production database from SQLite to PostgreSQL.

# \* Add production monitoring and error tracking.

# \* Deploy the backend using Railway, Render, AWS, or another cloud platform.

# \* Configure a custom domain for the production API.

# \* Add automated tests and CI/CD.

# 

# \## License

# 

# This project is currently intended for development, learning, and portfolio purposes.



