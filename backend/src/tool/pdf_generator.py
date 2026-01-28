import os
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors

class PDFGenerator:
    def __init__(self, output_dir: str = "./outputs"):
        self.output_dir = output_dir
        self._create_output_dir()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _create_output_dir(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    def _setup_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=12,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceAfter=10,
            leading=14
        ))

        self.styles.add(ParagraphStyle(
            name='CustomMeta',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#666666'),
            alignment=TA_LEFT,
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='Heading2',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=8,
            spaceBefore=12,
            alignment=TA_LEFT
        ))

    def generate_meaningful_filename(
        self,
        title: str,
        keyword: Optional[str] = None,
        url: Optional[str] = None
    ) -> str:
        parts = []
        
        if keyword:
            safe_keyword = "".join(c for c in keyword if c.isalnum() or c in ('-', '_')).lower()[:20]
            parts.append(safe_keyword)
        
        safe_title = "".join(c for c in title if c.isalnum() or c in ('-', '_')).lower()[:30]
        parts.append(safe_title)
        
        if url:
            domain = urlparse(url).netloc.replace('www.', '').split('.')[0]
            parts.append(domain)
        
        timestamp = datetime.now().strftime("%Y%m%d")
        parts.append(timestamp)
        
        filename = "_".join(filter(None, parts)) + ".pdf"
        return filename

    def generate_pdf(
        self,
        title: str,
        content: str,
        url: Optional[str] = None,
        filename: Optional[str] = None
    ) -> dict:
        try:
            if not filename:
                filename = self.generate_meaningful_filename(title, url=url)
            
            file_path = os.path.join(self.output_dir, filename)
            
            doc = SimpleDocTemplate(
                file_path,
                pagesize=letter,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch
            )
            
            story = []
            
            story.append(Paragraph(title, self.styles['CustomTitle']))
            story.append(Spacer(1, 0.2*inch))
            
            if url:
                story.append(Paragraph(f"<b>Source:</b> {url}", self.styles['CustomMeta']))
            
            story.append(Paragraph(
                f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                self.styles['CustomMeta']
            ))
            story.append(Spacer(1, 0.3*inch))
            
            # Better content parsing - handle markdown-style headings and lists
            lines = content.split('\n')
            current_paragraph = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    # Empty line - flush current paragraph
                    if current_paragraph:
                        para_text = ' '.join(current_paragraph)
                        story.append(Paragraph(para_text, self.styles['CustomBody']))
                        story.append(Spacer(1, 0.1*inch))
                        current_paragraph = []
                elif line.startswith('##'):
                    # Heading - flush paragraph first, then add heading
                    if current_paragraph:
                        para_text = ' '.join(current_paragraph)
                        story.append(Paragraph(para_text, self.styles['CustomBody']))
                        story.append(Spacer(1, 0.1*inch))
                        current_paragraph = []
                    # Add heading (remove ## and make bold)
                    heading_text = line.replace('##', '').strip()
                    story.append(Paragraph(f"<b>{heading_text}</b>", self.styles['Heading2']))
                    story.append(Spacer(1, 0.15*inch))
                elif line.startswith('-') or line.startswith('*'):
                    # Bullet point - flush paragraph, add bullet
                    if current_paragraph:
                        para_text = ' '.join(current_paragraph)
                        story.append(Paragraph(para_text, self.styles['CustomBody']))
                        story.append(Spacer(1, 0.1*inch))
                        current_paragraph = []
                    bullet_text = line.lstrip('-*').strip()
                    story.append(Paragraph(f"• {bullet_text}", self.styles['CustomBody']))
                    story.append(Spacer(1, 0.05*inch))
                else:
                    # Regular text - accumulate into paragraph
                    current_paragraph.append(line)
            
            # Flush any remaining paragraph
            if current_paragraph:
                para_text = ' '.join(current_paragraph)
                story.append(Paragraph(para_text, self.styles['CustomBody']))
                story.append(Spacer(1, 0.1*inch))

            doc.build(story)
            
            return {
                'success': True,
                'file_path': file_path,
                'filename': filename,
                'error': None
            }
        
        except Exception as e:
            error_msg = f"Error generating PDF: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'file_path': None,
                'filename': filename or 'unknown',
                'error': error_msg
            }

    def generate_pdf_from_web(
        self,
        title: str,
        content: str,
        url: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> dict:
        enhanced_content = content
        if keyword:
            enhanced_content = f"<b>Keyword Search:</b> {keyword}\n\n{content}"

        filename = self.generate_meaningful_filename(title, keyword=keyword, url=url)
        
        return self.generate_pdf(
            title=title,
            content=enhanced_content,
            url=url,
            filename=filename
        )


pdf_generator = PDFGenerator()

def save_to_pdf(
    title: str,
    content: str,
    url: Optional[str] = None,
    keyword: Optional[str] = None,
    output_dir: str = "./outputs"
) -> dict:
    generator = PDFGenerator(output_dir=output_dir)
    
    return generator.generate_pdf_from_web(
        title=title,
        content=content,
        url=url,
        keyword=keyword
    )