# Brazilian E-Commerce SQL Analytics

## Project Overview
This project is an end-to-end data pipeline and SQL analytics portfolio piece built during a 24-hour data sprint. It transforms 100,000+ rows of raw, real-world e-commerce data into a fully functional relational database to uncover business insights regarding customer behavior, revenue generation, and supply chain efficiency.

## Tech Stack
*   **Language:** Python 3.9
*   **Libraries:** `pandas`, `sqlite3`, `os`
*   **Database:** SQLite
*   **Environment:** Jupyter Notebooks / VS Code

---

## The Data Source
The dataset used in this project is the **Brazilian E-Commerce Public Dataset by Olist**, provided by Kaggle. It contains information on 100k orders made at multiple marketplaces in Brazil from 2016 to 2018.

**How to get the data:**
1. Create a free account on [Kaggle](https://www.kaggle.com/).
2. Search for `Brazilian E-Commerce Public Dataset by Olist`.
3. Download the archive and extract the CSV files.
4. Place the extracted CSV files into a folder named `/data` in the root of this repository. *(Note: The raw CSV files are ignored by git due to their size).*

---

## Project Structure
```text
ecommerce-sql-project/
├── data/                  <-- User must create this and add Kaggle CSVs
├── load_data.ipynb        <-- Python ETL script that builds the database
├── olist.db               <-- Generated SQLite database (Ignored in Git)
├── .gitignore             <-- Excludes environments and heavy data files
└── README.md              <-- Project documentation