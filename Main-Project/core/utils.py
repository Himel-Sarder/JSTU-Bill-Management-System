import os
import io
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import logging

logger = logging.getLogger(__name__)

def convert_to_bangla_digits(number):
    """Convert English digits to Bengali digits"""
    english_to_bangla = str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯')
    return str(number).translate(english_to_bangla)

def format_bangla_number(number):
    """Format number with Bengali digits and commas"""
    try:
        bangla_digits = '০১২৩৪৫৬৭৮৯'
        formatted = "{:,}".format(int(number))
        return ''.join(bangla_digits[int(char)] if char.isdigit() else char for char in formatted)
    except:
        return str(number)

def get_bangla_font_config():
    """Get Bengali font configuration for WeasyPrint"""
    font_config = FontConfiguration()
    
    # Try to find Bengali fonts
    font_paths = [
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Kalpurush.ttf'),
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'SolaimanLipi.ttf'),
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Nikosh.ttf'),
    ]
    
    css_rules = """
    @font-face {
        font-family: 'BanglaFont';
        src: url('file:///%s');
        font-weight: normal;
        font-style: normal;
    }
    
    @font-face {
        font-family: 'BanglaFont';
        src: url('file:///%s');
        font-weight: bold;
        font-style: normal;
    }
    """
    
    # Find the first available Bengali font
    available_font = None
    for font_path in font_paths:
        if os.path.exists(font_path):
            available_font = font_path
            logger.info(f"Using Bengali font: {font_path}")
            break
    
    if available_font:
        css = css_rules % (available_font, available_font)
    else:
        # Fallback to system fonts that might support Bengali
        css = """
        @font-face {
            font-family: 'BanglaFont';
            src: local('Arial Unicode MS'), local('Microsoft Sans Serif');
        }
        """
        logger.warning("No Bengali font found, using system fallback")
    
    return font_config, css

def render_to_pdf(template_src, context_dict={}):
    """Render HTML template to PDF using WeasyPrint"""
    try:
        template = get_template(template_src)
        html_content = template.render(context_dict)
        
        # Get font configuration
        font_config, font_css = get_bangla_font_config()
        
        # Create HTML object
        html = HTML(string=html_content, encoding='utf-8')
        
        # Additional CSS for PDF styling
        pdf_css = CSS(string='''
            %s
            body {
                font-family: 'BanglaFont', 'SolaimanLipi', 'Kalpurush', Arial, sans-serif;
                line-height: 1.4;
                color: #000;
                margin: 0;
                padding: 0;
            }
            
            .bangla-text {
                font-family: 'BanglaFont', 'SolaimanLipi', 'Kalpurush', Arial, sans-serif;
            }
            
            .bangla-digit {
                font-family: 'BanglaFont', 'SolaimanLipi', 'Kalpurush', Arial, sans-serif;
            }
            
            @page {
                size: A4;
                margin: 1.5cm;
                @bottom-center {
                    content: "পৃষ্ঠা " counter(page) " / " counter(pages);
                    font-family: 'BanglaFont', 'SolaimanLipi', 'Kalpurush', Arial, sans-serif;
                    font-size: 10px;
                    color: #666;
                }
            }
        ''' % font_css, font_config=font_config)
        
        # Generate PDF
        pdf_file = html.write_pdf(stylesheets=[pdf_css], font_config=font_config)
        
        return HttpResponse(pdf_file, content_type='application/pdf')
        
    except Exception as e:
        logger.error(f"Error in render_to_pdf: {e}")
        return None

def generate_bill_pdf(bill):
    """Generate PDF for a bill using WeasyPrint"""
    try:
        context = {
            'bill': bill,
            'tasks': bill.tasks.all(),
            'convert_to_bangla_digits': convert_to_bangla_digits,
            'format_bangla_number': format_bangla_number,
        }
        
        pdf = render_to_pdf('core/bill_pdf.html', context)
        
        if pdf:
            response = pdf
            filename = f"bill_{bill.bill_number}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            return HttpResponse(
                "Error generating PDF. Please check server logs.", 
                status=500
            )
    
    except Exception as e:
        logger.error(f"Error in generate_bill_pdf: {e}")
        return HttpResponse(
            f"Error generating PDF: {str(e)}", 
            status=500
        )