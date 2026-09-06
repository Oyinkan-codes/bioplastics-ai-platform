import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def build_loi_pdf():
    os.makedirs("docs", exist_ok=True)
    pdf_path = os.path.join("docs", "BioMatX_LOI.pdf")

    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    # Header / Branding
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "BioMatX AI Technologies Ltd.")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 65, "DeepTech AI Material Formulations | Licensing & SaaS Platform")
    c.drawString(50, height - 78, "Contact: commercial@biomatx.co.uk | London, UK")
    c.line(50, height - 90, width - 50, height - 90)

    # Document Title
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 120, "LETTER OF INTENT (LOI): B2B PILOT TESTING & LICENSING")

    # Content
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 145, "DATE:")
    c.setFont("Helvetica", 10)
    c.drawString(100, height - 145, "September 06, 2026")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 160, "PARTNER:")
    c.setFont("Helvetica", 10)
    c.drawString(100, height - 160, "[Partner UK Packaging / FMCG Company Name]")

    c.setFont("Helvetica", 10)
    text_y = height - 190

    paragraphs = [
        "1. INTENT OF AGREEMENT: The undersigned partner expresses a formal expression of interest to test, validate, and evaluate proprietary bioplastic formulations designed by BioMatX AI Technologies Ltd.",
        "2. TECHNICAL FOCUS: The pilot trial will target high-barrier bio-polymer formulations derived from local agricultural waste streams (including Cassava Processing Waste and Brewery Spent Grain).",
        "3. ASSET-LIGHT LICENSING MODEL: Upon successful lab validation, the Partner intends to enter negotiations to license BioMatX formulation IP for commercial manufacturing using existing UK plastic production lines.",
        "4. NON-BINDING NATURE: This Letter of Intent represents a commercial expression of mutual interest and pilot testing commitment for visa endorsement and commercial validation purposes, but does not constitute a legally binding purchase obligation until a final Master Licensing Agreement is executed."
    ]

    for paragraph in paragraphs:
        words = paragraph.split(" ")
        line = ""
        for word in words:
            if len(line + " " + word) < 85:
                line += " " + word
            else:
                c.drawString(50, text_y, line.strip())
                text_y -= 15
                line = word
        if line:
            c.drawString(50, text_y, line.strip())
            text_y -= 25

    # Signatures
    text_y -= 20
    c.line(50, text_y, width - 50, text_y)
    text_y -= 25

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, text_y, "EXECUTED AND ACKNOWLEDGED BY:")

    text_y -= 50
    c.line(50, text_y, 250, text_y)
    c.drawString(50, text_y - 15, "Authorized Signatory: BioMatX AI")
    c.drawString(50, text_y - 30, "Title: Founder & Chief Technology Officer")

    c.line(320, text_y, 520, text_y)
    c.drawString(320, text_y - 15, "Authorized Signatory: Partner Firm")
    c.drawString(320, text_y - 30, "Title: Commercial / Procurement Director")

    c.save()

if __name__ == "__main__":
    build_loi_pdf()
