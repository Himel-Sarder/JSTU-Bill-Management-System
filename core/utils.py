import os
import io
import logging
import base64
import tempfile
import shutil
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
from django.contrib.auth.models import User
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

logger = logging.getLogger(__name__)


def field_to_base64(field):
    """Read an ImageField/FileField into a base64 data URL.

    Deliberately avoids `.path` — that only works for local filesystem
    storage and raises NotImplementedError on cloud storages such as
    Cloudinary (which this project uses for MEDIA files). `field.open()`
    works correctly with any storage backend.
    """
    if not field:
        return None
    try:
        field.open('rb')
        try:
            image_data = field.read()
        finally:
            field.close()
        base64_string = base64.b64encode(image_data).decode('utf-8')
        ext = os.path.splitext(field.name)[1].lower()
        mime_type = 'image/png' if ext == '.png' else 'image/jpeg'
        return f"data:{mime_type};base64,{base64_string}"
    except Exception as e:
        logger.error(f"Error reading signature file '{getattr(field, 'name', field)}': {e}")
        return None

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
    
    font_paths = [
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Kalpurush.ttf'),
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'SolaimanLipi.ttf'),
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Nikosh.ttf'),
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'BanglaFont.ttf'),
    ]
    
    available_font = None
    for font_path in font_paths:
        if os.path.exists(font_path):
            available_font = font_path
            logger.info(f"Using Bengali font: {font_path}")
            break
    
    if available_font:
        css = f"""
        @font-face {{
            font-family: 'BanglaFont';
            src: url('file:///{available_font}');
            font-weight: normal;
            font-style: normal;
        }}
        """
    else:
        css = """
        @font-face {
            font-family: 'BanglaFont';
            src: local('Arial Unicode MS'), local('Microsoft Sans Serif');
        }
        """
        logger.warning("No Bengali font found")
    
    return font_config, css

def render_to_pdf(template_src, context_dict={}):
    """Render HTML template to PDF using WeasyPrint"""
    temp_file = None
    try:
        template = get_template(template_src)
        html_content = template.render(context_dict)
        
        font_config, font_css = get_bangla_font_config()
        
        pdf_css = CSS(string=f'''
            {font_css}
            body {{
                font-family: 'BanglaFont', 'SolaimanLipi', 'Kalpurush', 'Arial Unicode MS', sans-serif;
                line-height: 1.4;
                color: #000;
                margin: 0;
                padding: 0;
                font-size: 12px;
            }}
            
            .bangla-text, .bangla-digit {{
                font-family: 'BanglaFont', 'SolaimanLipi', 'Kalpurush', 'Arial Unicode MS', sans-serif;
            }}
            
            @page {{
                size: legal;
                margin: 1.5cm;
                @bottom-center {{
                    content: "পৃষ্ঠা " counter(page) " / " counter(pages);
                    font-size: 9px;
                    color: #666;
                }}
            }}
            
            .tasks-table {{
                width: 100%;
                border-collapse: collapse;
                border: 2px solid #333;
                font-size: 11px;
            }}
            
            .tasks-table th, .tasks-table td {{
                border: 1px solid #333;
                padding: 6px 4px;
            }}
            
            .tasks-table th {{
                background: #f0f0f0;
                font-weight: bold;
            }}
            
            .signature-line {{
                border-top: 1px solid #000;
                width: 200px;
                margin: 5px 0;
            }}
            
            .chairman-signature-img {{
                max-width: 180px;
                max-height: 70px;
                object-fit: contain;
                margin-bottom: 10px;
            }}
            
            .signature-with-img {{
                text-align: center;
            }}
        ''', font_config=font_config)
        
        html = HTML(string=html_content, base_url=settings.BASE_DIR, encoding='utf-8')
        pdf_file = html.write_pdf(stylesheets=[pdf_css], font_config=font_config)
        
        return pdf_file
        
    except Exception as e:
        logger.error(f"Error in render_to_pdf: {e}")
        return None
    finally:
        # Clean up temp file if created
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

def render_bills_report_pdf(context):
    """Render a filtered list of bills as a landscape summary PDF report using WeasyPrint"""
    try:
        template = get_template('core/bills_report_pdf.html')
        html_content = template.render(context)

        font_config, font_css = get_bangla_font_config()

        pdf_css = CSS(string=f'''
            {font_css}
            body {{
                font-family: 'BanglaFont', 'SolaimanLipi', 'Kalpurush', 'Arial Unicode MS', sans-serif;
                line-height: 1.4;
                color: #000;
                margin: 0;
                padding: 0;
                font-size: 10px;
            }}

            .bangla-text, .bangla-digit {{
                font-family: 'BanglaFont', 'SolaimanLipi', 'Kalpurush', 'Arial Unicode MS', sans-serif;
            }}

            @page {{
                size: A4 landscape;
                margin: 1.2cm;
                @bottom-center {{
                    content: "পৃষ্ঠা " counter(page) " / " counter(pages);
                    font-size: 8px;
                    color: #666;
                }}
            }}

            .report-table {{
                width: 100%;
                border-collapse: collapse;
                border: 1.5px solid #333;
                font-size: 9.5px;
            }}

            .report-table th, .report-table td {{
                border: 1px solid #333;
                padding: 5px 4px;
            }}

            .report-table th {{
                background: #e2e2e2;
                font-weight: bold;
                text-align: center;
            }}

            .report-table tfoot td {{
                background: #f0f0f0;
                font-weight: bold;
            }}
        ''', font_config=font_config)

        html = HTML(string=html_content, base_url=settings.BASE_DIR, encoding='utf-8')
        pdf_file = html.write_pdf(stylesheets=[pdf_css], font_config=font_config)

        return pdf_file

    except Exception as e:
        logger.error(f"Error in render_bills_report_pdf: {e}")
        return None

def render_accepted_summary_pdf(context):
    """Render the consolidated accepted-bills report (landscape A4).

    Reuses the same Bangla font setup as the other reports; the layout lives in
    accepted_bills_report_pdf.html.
    """
    try:
        template = get_template('core/accepted_bills_report_pdf.html')
        html_content = template.render(context)

        font_config, font_css = get_bangla_font_config()

        pdf_css = CSS(string=f"""
            {font_css}
            body {{
                font-family: 'BanglaFont', 'SolaimanLipi', 'Kalpurush', 'Arial Unicode MS', sans-serif;
                line-height: 1.35;
                color: #000;
                margin: 0;
                padding: 0;
            }}
            .bangla-text {{
                font-family: 'BanglaFont', 'SolaimanLipi', 'Kalpurush', 'Arial Unicode MS', sans-serif;
            }}
        """, font_config=font_config)

        html = HTML(string=html_content, base_url=settings.WEASYPRINT_BASEURL)
        pdf_file = html.write_pdf(stylesheets=[pdf_css], font_config=font_config)

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="accepted-bills-summary.pdf"'
        return response

    except Exception as e:
        logger.error(f"Error in render_accepted_summary_pdf: {e}")
        return HttpResponse('PDF তৈরি করা যায়নি।', status=500)


def get_chairman_signature_for_bill(bill):
    """The signature of the chairman who owns this bill, as a base64 data URL.

    Resolution order:
      1. whoever actually approved the bill, if they are a chairman
      2. otherwise the chairman for the bill's academic year AND department

    The previous version parsed a hardcoded username (JSTUChairman1..4) out of
    bill.remarks. That could only ever name four people university-wide, and
    with several departments it would hand one department's signature to
    another department's bill. Year plus department is now the key.
    """
    logger.info(f"=== Getting signature for bill {bill.bill_number} ===")

    chairman = None

    # 1. The approver, when they are a chairman
    approver = bill.approved_by
    if approver is not None:
        approver_profile = getattr(approver, 'profile', None)
        if approver_profile is not None and approver_profile.user_type == 'চেয়ারম্যান':
            chairman = approver

    # 2. Fall back to the chairman for this bill's year and department
    if chairman is None:
        chairman = bill.chairman

    if chairman is None:
        logger.info(f"No chairman resolved for bill {bill.bill_number}")
        return None

    profile = getattr(chairman, 'profile', None)
    if profile is None:
        logger.warning(f"Chairman {chairman.username} has no profile")
        return None

    signature_field = profile.active_chairman_signature
    if not signature_field:
        logger.warning(f"No signature file for chairman {chairman.username}")
        return None

    data_url = field_to_base64(signature_field)
    if not data_url:
        logger.warning(f"Could not read signature file for {chairman.username}")
        return None

    logger.info(f"Signature resolved for {chairman.username}, length: {len(data_url)}")
    return data_url


def generate_bill_pdf_chairman(bill, inline=False):
    """Generate PDF for chairman with signature"""
    try:
        tasks = bill.tasks.all()
        chairman_signature = get_chairman_signature_for_bill(bill)
        
        logger.info(f"Generating PDF for bill {bill.bill_number}")
        logger.info(f"Signature found: {bool(chairman_signature)}")
        
        context = {
            'bill': bill,
            'tasks': tasks,
            'chairman_signature': chairman_signature,
            'convert_to_bangla_digits': convert_to_bangla_digits,
            'format_bangla_number': format_bangla_number,
        }
        
        pdf_content = render_to_pdf('core/bill_pdfchairman1.html', context)
        
        if pdf_content:
            response = HttpResponse(pdf_content, content_type='application/pdf')
            filename = f"bill_{bill.bill_number}.pdf"
            
            if inline:
                response['Content-Disposition'] = f'inline; filename="{filename}"'
            else:
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
        else:
            return HttpResponse("Error generating PDF", status=500)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return HttpResponse(f"Error: {str(e)}", status=500)

def generate_bill_pdf_user(bill, inline=False):
    """Generate PDF for regular users"""
    try:
        tasks = bill.tasks.all()
        
        user_signature = None
        if hasattr(bill.user, 'profile') and bill.user.profile.signature_general:
            user_signature = field_to_base64(bill.user.profile.signature_general)
        
        context = {
            'bill': bill,
            'tasks': tasks,
            'user_signature': user_signature,
            'convert_to_bangla_digits': convert_to_bangla_digits,
            'format_bangla_number': format_bangla_number,
        }
        
        pdf_content = render_to_pdf('core/bill_pdfuser.html', context)
        
        if pdf_content:
            response = HttpResponse(pdf_content, content_type='application/pdf')
            filename = f"bill_{bill.bill_number}.pdf"
            
            if inline:
                response['Content-Disposition'] = f'inline; filename="{filename}"'
            else:
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
        else:
            return HttpResponse("Error generating PDF", status=500)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return HttpResponse(f"Error: {str(e)}", status=500)

def generate_bill_pdf(bill, inline=False):
    """Generate PDF with both user and chairman signatures permanently"""
    try:
        tasks = bill.tasks.all()
        
        # Get user's signature ONLY if user_signature_added is True
        user_signature = None
        if bill.user_signature_added and hasattr(bill.user, 'profile') and bill.user.profile.signature_general:
            user_signature = field_to_base64(bill.user.profile.signature_general)
        
        # Get chairman's signature if it was added (permanently - regardless of current status)
        # This is the key fix - check if signature was added, not just current status
        chairman_signature = None
        if bill.chairman_signature_added:
            chairman_signature = get_chairman_signature_for_bill(bill)
        
        context = {
            'bill': bill,
            'tasks': tasks,
            'user_signature': user_signature,
            'chairman_signature': chairman_signature,
            'convert_to_bangla_digits': convert_to_bangla_digits,
            'format_bangla_number': format_bangla_number,
        }
        
        pdf_content = render_to_pdf('core/bill_pdf.html', context)
        
        if pdf_content:
            response = HttpResponse(pdf_content, content_type='application/pdf')
            filename = f"bill_{bill.bill_number}.pdf"
            disposition = 'inline' if inline else 'attachment'
            response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
            return response
        else:
            return HttpResponse("Error generating PDF", status=500)
    
    except Exception as e:
        logger.error(f"Error in generate_bill_pdf: {e}")
        return HttpResponse(f"Error: {str(e)}", status=500)
    
def generate_bill_pdf_download(bill):
    return generate_bill_pdf(bill, inline=False)

def generate_bill_pdf_view(bill):
    return generate_bill_pdf(bill, inline=True)