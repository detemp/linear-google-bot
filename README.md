### 

# **Linear for Permittable (Google Chat Plugin)**

This is a custom Google Chat integration designed for **permittable.ai**. It allows the team to manage Linear issues directly from chat without switching tabs.

## **🚀 Commands**

| Command | Usage | Description |
| :---- | :---- | :---- |
| /new | /new \[Title\] \[Keywords\] | Creates a new Linear issue. |
| /list | /list | Displays the 5 most recent issues for the team. |
| /update | /update \[ID\] \[New Title\] | Updates the title of an existing issue (e.g., ENG-123). |

## ---

**💡 Smart Logic**

The /new command is equipped with basic Natural Language Processing (NLP) to help triage issues as you type them.

### **Priority Detection**

If you include any of these keywords in your message, the bot will automatically set the issue priority:

* **Urgent** → Priority 1  
* **High** → Priority 2  
* **Medium** → Priority 3  
* **Low** → Priority 4

### **Auto-Labeling**

The bot scans for specific keywords to apply labels:

* **"bug"** → Automatically applies the **Bug** label.  
* **"feat"** or **"request"** → Automatically applies the **Feature** label.

**Example:** /new urgent bug Permit scraper is timing out

* **Result:** Creates a Linear issue with **Priority: Urgent** and the **Bug** label.

## ---

**🛠 Tech Stack & Maintenance**

* **Language:** Python 3.12 (Flask)  
* **Cloud:** Google Cloud Functions (2nd Gen)  
* **CI/CD:** Automated via GitHub Actions / Cloud Build.  
* **Secrets:** Managed via Google Secret Manager.

### **Making Changes**

1. Clone this repository.  
2. Modify main.py (e.g., to add new label keywords).  
3. Push to main.  
4. The bot will automatically redeploy via Cloud Build (\~2 minutes).

### **Environment Variables**

If the bot stops responding, ensure the following are correctly set in Google Secret Manager:

* LINEAR\_API\_KEY: Your Personal Access Token.  
* LINEAR\_TEAM\_ID: The UUID for the Permittable team in Linear.

