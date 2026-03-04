# scripts/seed_documents.py
from apps.lawfirms.models import Case, Document
from faker import Faker

fake = Faker()

cases = Case.objects.all()
for case in cases:
    for _ in range(3):  # 3 documents per case
        doc = Document.objects.create(
            case=case,
            title=fake.sentence(),
            content=fake.paragraph(nb_sentences=5)
        )
        print(f"✅ Created Document: {doc.title} (Case: {case.case_number})")