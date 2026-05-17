# Software Engineering Project  
## Digital Onboarding Management System – Paoli Group

> ⚠️ **Important:**  
> The full project documentation, architecture diagrams, requirements analysis, and design decisions are available in:  
>
> 📄 **[Phase 3 – Paoli Group.pdf](./Phase%203%20-%20Paoli%20Group.pdf)**  
>
> Professionals reviewing this repository are strongly encouraged to read the PDF for complete technical context.

---

## Project Overview

This project was developed as part of a Software Engineering course in collaboration with **Paoli Group LLC**.

It is a prototype **Digital Onboarding Management System** designed to:

- Streamline employee onboarding workflows  
- Manage documentation securely  
- Track onboarding progress  
- Separate roles and permissions  
- Maintain structured backend architecture  

The repository contains the working implementation.  
The PDF contains the full engineering documentation.

---

## Engineering Focus

This project demonstrates:

- Requirements Engineering
- System Modeling
- Architectural Design
- Modular Backend Structure
- Frontend–Backend Separation
- Database Schema Design
- Document Handling

---
---

## Technologies Used

- Python (Backend)
- HTML / CSS / JavaScript (Frontend)
- SQL Database
- REST-style routing
- File upload handling

---

## Running the Project

### Clone
```bash
git clone https://github.com/kevinsantiagomatos/Software-Engineering-Project.git
cd Software-Engineering-Project
```

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Database
Canonical bootstrap schema:

`backend/sql/paolischema.sql`

Manual import:
```bash
mysql -u root -p palogroup < backend/sql/paolischema.sql
```

If upgrading an older snapshot, apply migrations in order:

- `backend/sql/migrations/20260421_role_department_model.sql`
- `backend/sql/migrations/20260422_it_access_checklist.sql`
- `backend/sql/migrations/20260511_compliance_review_workflow.sql`

The backend can also auto-initialize missing tables on startup.  
To disable auto-init:
```bash
export DB_AUTO_INIT=false
```

### Start Backend
```bash
cd backend
python app.py
```

### Frontend (Optional Static Preview)
```bash
cd front_end
python -m http.server 8000
```
