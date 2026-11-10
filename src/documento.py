"""Formato normal de Word: Times New Roman 12, negro y márgenes de 2,54 cm."""
from html.parser import HTMLParser
from pathlib import Path
import re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT


class Texto(HTMLParser):
    def __init__(self, paragraph):
        super().__init__(); self.p=paragraph; self.bold=False;self.href=None
    def handle_starttag(self, tag, attrs):
        if tag=='b': self.bold=True
        if tag=='br': self.p.add_run().add_break()
        if tag=='link':self.href=dict(attrs).get('href')
    def handle_endtag(self, tag):
        if tag=='b': self.bold=False
        if tag=='link':self.href=None
    def handle_data(self, data):
        if self.href:
            h=OxmlElement('w:hyperlink');h.set(qn('r:id'),self.p.part.relate_to(self.href,RT.HYPERLINK,is_external=True))
            run=OxmlElement('w:r');rp=OxmlElement('w:rPr')
            color=OxmlElement('w:color');color.set(qn('w:val'),'000000');rp.append(color)
            u=OxmlElement('w:u');u.set(qn('w:val'),'single');rp.append(u);run.append(rp)
            t=OxmlElement('w:t');t.text=data;run.append(t);h.append(run);self.p._p.append(h);return
        for part in re.split(r'(_(?:\d+|[hir]))(?=[^A-Za-z0-9]|$)',data):
            sub=bool(re.fullmatch(r'_(?:\d+|[hir])',part))
            r=self.p.add_run(part[1:] if sub else part)
            if self.bold:r.bold=True
            if sub:r.font.subscript=True


class InformeWord:
    def __init__(self):
        self.doc=Document(); self.ancho=6.5
        sec=self.doc.sections[0]
        sec.page_width=Inches(8.5); sec.page_height=Inches(11)
        sec.top_margin=sec.bottom_margin=sec.left_margin=sec.right_margin=Inches(1)
        sec.header_distance=sec.footer_distance=Inches(.5)
        sec.different_first_page_header_footer=True
        for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','Caption','List Paragraph','Footer']:
            s=self.doc.styles[name]; s.font.name='Times New Roman'; s.font.size=Pt(12)
            s.font.color.rgb=RGBColor(0,0,0)
            s._element.get_or_add_rPr().rFonts.set(qn('w:hAnsi'),'Times New Roman')
            fonts=s._element.get_or_add_rPr().rFonts
            for attr in ['asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme']:
                fonts.attrib.pop(qn('w:'+attr),None)
            s.paragraph_format.line_spacing=1.5
            s.paragraph_format.space_after=Pt(6)
            s.paragraph_format.widow_control=True
            if name in ['Title','Heading 1','Heading 2']:
                s.font.bold=True; s.paragraph_format.keep_with_next=True
                s.paragraph_format.space_before=Pt(12)
            if name in ['Heading 1','Heading 2']:
                s.paragraph_format.page_break_before=False
        for style in self.doc.styles:
            for border in list(style._element.iter(qn('w:pBdr'))):border.getparent().remove(border)
        p=sec.footer.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        fld=OxmlElement('w:fldSimple'); fld.set(qn('w:instr'),'PAGE'); p._p.append(fld)
        self.doc.core_properties.title='Simulación y optimización de un call-center'
        self.doc.core_properties.author='Fabian Prado; Diego Sandoval; Yehosua Hercules'

    def para(self,text,style='Cuerpo'):
        names={'Cuerpo':'Normal','Titulo2':'Heading 1','Sub':'Heading 2','Peq':'Normal','Portada':'Title','Formula':'Normal'}
        p=self.doc.add_paragraph(style=names[style]); Texto(p).feed(text)
        if style=='Cuerpo':p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
        if style in ['Peq','Formula']:p.paragraph_format.line_spacing=1.0
        if style=='Formula':p.paragraph_format.left_indent=Inches(.15)
        return p

    def tabla(self,data,widths=None):
        t=self.doc.add_table(rows=0,cols=len(data[0])); t.alignment=WD_TABLE_ALIGNMENT.CENTER
        t.autofit=False
        total=sum(widths) if widths else len(data[0])
        pesos=widths if widths else [1]*len(data[0])
        for c,w in zip(t.columns,pesos):c.width=Inches(self.ancho*w/total)
        borders=OxmlElement('w:tblBorders')
        for side in ['top','left','bottom','right','insideH','insideV']:
            e=OxmlElement('w:'+side); e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'BFBFBF');borders.append(e)
        t._tbl.tblPr.append(borders)
        for i,row in enumerate(data):
            cells=t.add_row().cells
            trpr=cells[0]._tc.getparent().get_or_add_trPr()
            ns=OxmlElement('w:cantSplit');trpr.append(ns)
            if i==0:
                repeat=OxmlElement('w:tblHeader');trpr.append(repeat)
            for j,(cell,value,w) in enumerate(zip(cells,row,pesos)):
                cell.width=Inches(self.ancho*w/total);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                p=cell.paragraphs[0];p.paragraph_format.line_spacing=1.0
                if len(data)<=5 and i<len(data)-1:p.paragraph_format.keep_with_next=True
                p.paragraph_format.space_before=Pt(4);p.paragraph_format.space_after=Pt(4)
                Texto(p).feed(str(value))
                if i==0:
                    for run in p.runs:run.bold=True
                if j>0 and len(str(value))<22:p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        self.doc.add_paragraph().paragraph_format.space_after=Pt(0)
        return t

    def figura(self,path,caption):
        p=self.doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next=True;p.paragraph_format.space_after=Pt(3)
        p.add_run().add_picture(str(path),width=Inches(self.ancho))
        c=self.para(caption,'Peq');c.paragraph_format.space_after=Pt(9)

    def portada(self,equipo):
        for text in ['Universidad del Valle de Guatemala','CC3074 Modelización y Simulación','Ciclo 2 de 2026']:
            self.para(text).alignment=WD_ALIGN_PARAGRAPH.CENTER
        self.doc.add_paragraph(); self.doc.add_paragraph()
        self.para('Proyecto 2','Portada').alignment=WD_ALIGN_PARAGRAPH.CENTER
        self.para('Simulación y optimización de un call-center','Portada').alignment=WD_ALIGN_PARAGRAPH.CENTER
        self.para('Redistribución de capacidad con eventos discretos y recocido simulado').alignment=WD_ALIGN_PARAGRAPH.CENTER
        self.doc.add_paragraph(); self.doc.add_paragraph()
        for x in equipo['integrantes']:
            self.para(x['nombre']+' — '+x['carne']).alignment=WD_ALIGN_PARAGRAPH.CENTER
        self.doc.add_paragraph();self.doc.add_paragraph()
        self.para('10 de noviembre de 2026').alignment=WD_ALIGN_PARAGRAPH.CENTER
        self.para('<link href="https://github.com/yehosuah/proyecto-2-callcenter-uvg-2026">github.com/yehosuah/proyecto-2-callcenter-uvg-2026</link>').alignment=WD_ALIGN_PARAGRAPH.CENTER
        self.doc.add_page_break()

    def guardar(self,path):
        for run in self.doc.element.iter(qn('w:r')):
            rp=run.find(qn('w:rPr'))
            if rp is None:rp=OxmlElement('w:rPr');run.insert(0,rp)
            fonts=rp.find(qn('w:rFonts'))
            if fonts is None:fonts=OxmlElement('w:rFonts');rp.insert(0,fonts)
            fonts.attrib.clear()
            for attr in ['ascii','hAnsi','eastAsia','cs']:fonts.set(qn('w:'+attr),'Times New Roman')
            size=rp.find(qn('w:sz'))
            if size is None:size=OxmlElement('w:sz');rp.append(size)
            size.set(qn('w:val'),'24')
        Path(path).parent.mkdir(parents=True,exist_ok=True);self.doc.save(path)
