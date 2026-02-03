import re
import time
import random
import logging
import requests
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from paper_elements import Paper, Section, Paragraph


@dataclass
class HTMLSection:
    numbers: List[int]
    level: int
    title: str
    element: Optional[ET.Element]
    paragraphs: List[str]


class XMLPaperParser:
    NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

    # Regex patterns for section numbering
    SECTION_PATTERN = re.compile(r'^((?:\d+\.)*\d+)\.?(?:\s+(.*?))?$')
    SECTION_NUMBER_PATTERN = re.compile(r'^((?:\d+\.)*\d+)\.\s+')
    
    # Keywords that often indicate non-section headings
    NON_SECTION_KEYWORDS = [
        'figure', 'fig', 'table', 'theorem', 'lemma', 'proposition', 
        'corollary', 'definition', 'remark', 'example', 'proof',
        'algorithm', 'equation', 'appendix'
    ]
    
    def __init__(self):       
        self.current_section_hierarchy = []
        self.citation_map = {} 
            
    def parse(self, xml_content: str) -> Paper:
        """
        Parse GROBID TEI XML output into a Paper object.
        
        Args:
            xml_content: TEI XML string from GROBID
            
        Returns:
            Paper object containing the structured paper data
        """
        root = ET.fromstring(xml_content)
        
        # Create the root Paper object
        paper = Paper(name="root", father=None)
        
        # Extract metadata
        paper.title = self._extract_title(root)
        paper.author = self._extract_authors_string(root)
        
        # Extract abstract
        paper.abstract = self._extract_abstract(root, paper)
        
        # Extract body sections
        self._extract_body_sections(root, paper)
        
        return paper
    
    def _extract_title(self, root: ET.Element) -> str:
        """Extract paper title."""
        title_elem = root.find('.//tei:titleStmt/tei:title', self.NS)
        return title_elem.text if title_elem is not None else ""
    
    def _extract_authors_string(self, root: ET.Element) -> str:
        """Extract authors as a formatted string."""
        authors = []
        
        for author in root.findall('.//tei:sourceDesc//tei:author', self.NS):
            persname = author.find('.//tei:persName', self.NS)
            if persname is not None:
                forename = persname.find('.//tei:forename[@type="first"]', self.NS)
                surname = persname.find('.//tei:surname', self.NS)
                
                first = forename.text if forename is not None else ""
                last = surname.text if surname is not None else ""
                full_name = f"{first} {last}".strip()
                if full_name:
                    authors.append(full_name)
        
        return ", ".join(authors)
    
    def _extract_abstract(self, root: ET.Element, paper: Paper) -> Optional[Section]:
        """Extract abstract as a Section."""
        abstract_elem = root.find('.//tei:profileDesc/tei:abstract', self.NS)
        if abstract_elem is None:
            return None
        
        abstract_section = Section(name="Abstract", father=paper)
        
        # Extract paragraphs from abstract
        for div in abstract_elem.findall('.//tei:div', self.NS):
            for p_elem in div.findall('.//tei:p', self.NS):
                text = self._extract_text_from_element(p_elem)
                paragraph = Paragraph(father=abstract_section, text=text)
                abstract_section.add_paragraph(paragraph)
        
        # If no divs, try direct paragraphs
        if not abstract_section.paragraphs:
            for p_elem in abstract_elem.findall('.//tei:p', self.NS):
                text = self._extract_text_from_element(p_elem)
                paragraph = Paragraph(father=abstract_section, text=text)
                abstract_section.add_paragraph(paragraph)
        
        return abstract_section if abstract_section.paragraphs else None
   
    def _extract_body_sections(self, root: ET.Element, paper: Paper):
        """Extract body sections with hierarchical structure."""
        body = root.find('.//tei:text/tei:body', self.NS)
        if body is None:
            return
        
        # GROBID返回的XML文件往往不会按照你所期望的那样分好head，那最好的方法就是先提取整段文本再分割。
        pseudo_sections = []
        for div in body.findall('./tei:div', self.NS):
            sections = self._parse_div_with_complex_paragraphs(div)
            pseudo_sections.extend(sections)
        
        # 将section按照层级转化为Section类，需要分割句子。
        try:
            # 没有标题的情形
            last_chapter = [1]
            current_level = 1  # 当前节点的层级
            father_section = paper  # 当前节点的father
            if pseudo_sections[0].level == -1: paper.has_section_index = False
            for section in pseudo_sections:
                # 需要回溯
                if paper.has_section_index:
                    while current_level > section.level or (current_level >= 2 and section.numbers[current_level - 2] != last_chapter[current_level - 2]):
                        father_section = father_section.father
                        current_level -= 1
                    # 一次进两级，说明丢失了其中的一级
                    while current_level < section.level:
                        new_section = Section(name="", father=father_section)
                        father_section.add_child(new_section)
                        father_section = new_section
                        current_level += 1

                    last_chapter = section.numbers

                # 构建新的Section
                new_section = Section(section.title, father_section)
                # 将section.paragraph转化成Paragraph。先实现简单的句子分割，等以后再实现提取引用。
                for paragraph_text in section.paragraphs:
                    new_section.add_paragraph(Paragraph(father=new_section, text=paragraph_text))
                father_section.add_child(new_section)

                if paper.has_section_index:
                    # 默认将下一个Section设为当前Section的subsection，即默认进一级
                    current_level = section.level + 1
                    father_section = new_section
        except Exception as e:
            logging.warning(f" get {e}, fallback to parse paragraphs")
            self._fallback_parse_paragraphs(paper, body)
       
    def _extract_text_from_element(self, element: ET.Element):
        current_text = []
        
        def process_elem(element: ET.Element, depth=0):
            # Add text before element
            if element.text:
                current_text.append(element.text)
            
            # Skip citation references
            if element.tag != f"{{{self.NS['tei']}}}ref":
                for child in element:
                    process_elem(child, depth + 1)
            
            # Add text after element
            if element.tail and depth > 0:
                current_text.append(element.tail)
        
        # Process the paragraph element
        process_elem(element)
        
        return ''.join(current_text).strip()

    def _is_section_title(self, element: ET.Element) -> bool:
        """
        判断head元素是否是章节标题
        """
        text = self._extract_text_from_element(element)
        n_attr = element.get('n')
        if n_attr and n_attr.strip(): text = f"{n_attr.strip()} {text}"

        text_lower = text.lower().strip()
        if any(text_lower.startswith(x) for x in self.NON_SECTION_KEYWORDS): 
            return None, None
        
        # 检查是否包含典型的章节模式
        if self.SECTION_NUMBER_PATTERN.match(text):
            return True
        
        return False

    def _parse_section_title_from_p(self, text: str, element_type: str, n_attr: Optional[str] = None) -> Tuple[List[int], str]:
        """
        判断p元素的内容是否含有标题
        """
        if element_type == "head" and n_attr and n_attr.strip():
            text = f"{n_attr.strip()} {text}"
        text_lower = text.lower().strip()
        if any(text_lower.startswith(x) for x in self.NON_SECTION_KEYWORDS): 
            return None, None
        
        numbers, title = self._parse_section_number(text, element_type)
        if numbers and (element_type == "head" or self._compare_section_levels(numbers) != 2):
            return numbers, title
        
        return None, None
    
    def _parse_section_number(self, text: str, element_type: str, n_attr: Optional[str] = None) -> Tuple[List[int], str]:
        """
        解析章节号和标题文本
        参数:
            text: 标题文本
            n_attr: head元素的n属性值
        返回: (章节号列表, 标题文本)
        """
        # 优先使用n属性中的章节号
        text = text.strip()
        if element_type == "head" and n_attr and n_attr.strip():
            # 清理n属性中的章节号
            n_attr_clean = n_attr.strip().rstrip('.')
            match = self.SECTION_PATTERN.match(n_attr_clean)
            if match:
                numbers = match.group(1).split('.')
                # 如果n属性中有章节号，但文本中没有，使用文本作为标题
                title = text if text else (match.group(2).strip() if match.group(2) else "")
                return [int(num) for num in numbers], title
        
        # 如果没有n属性或n属性中没有有效的章节号，从文本中解析
        if text:
            if element_type == "head":
                section_id = self.SECTION_PATTERN.findall(text)
                if section_id:
                    section_id = section_id[0]
                    numbers = section_id[0].split('.')
                    title = section_id[1].strip() if len(section_id) >= 2 else ""
                    return [int(num) for num in numbers], title
            else:
                section_id = self.SECTION_NUMBER_PATTERN.match(text)
                if section_id:
                    numbers = section_id.group(1)
                    text = text.replace(numbers, "", 1).lstrip()
                    if text[0] == ".": text = text[1:].lstrip()
                    text_split = re.split(r'(?<=[.!?])\s+', text, 1)
                    return [int(num) for num in numbers.split('.')], text_split
        
        return None, text
    
    def _compare_section_levels(self, new_numbers: List[int]) -> int:
        """
        比较新章节号与当前层级的关系
        返回: 
          -1: 新章节是更高级别
          0: 同级
          1: 子级
        """
        if not self.current_section_hierarchy:
            return 1  # 第一个章节
        
        current = self.current_section_hierarchy[-1].numbers
        
        # 检查是否是直接子级
        if len(new_numbers) == len(current) + 1 and new_numbers[:-1] == current and new_numbers[-1] in [0, 1]:
            return 1
        
        # 检查同级
        if len(new_numbers) == len(current):
            if new_numbers[:-1] == current[:-1] and new_numbers[-1] == current[-1] + 1:
                return 0
        
        # 检查更高级别
        for i, j in zip(current, new_numbers):
            if j == i + 1: return -1
            elif i != j: break
        
        # 章节序号错误请检查
        return 2
    
    def _update_section_hierarchy(self, numbers: List[int], title: str, element: ET.Element, text: str = "") -> HTMLSection:
        """
        更新章节层级并返回当前章节信息
        """
        if not numbers:
            # 没有明确章节号，作为当前章节的子级处理
            if self.current_section_hierarchy:
                parent_numbers = self.current_section_hierarchy[-1].numbers
                numbers = parent_numbers + [1]  # 默认作为第一个子节
            else:
                numbers = [1]  # 第一个章节
        
        relation = self._compare_section_levels(numbers)
        
        if relation == -1:  # 更高级别
            # 回溯到合适层级
            while self.current_section_hierarchy:
                current = self.current_section_hierarchy[-1].numbers
                if len(numbers) <= len(current) and all(a == b for a, b in zip(numbers, current[:len(numbers)])):
                    break
                self.current_section_hierarchy.pop()
        
        elif relation == 2:
            # 寻找最近的共同祖先
            new_hierarchy = []
            for section in self.current_section_hierarchy:
                if (len(section.numbers) <= len(numbers) and 
                    section.numbers == numbers[:len(section.numbers)]):
                    new_hierarchy.append(section)
                else:
                    break
            self.current_section_hierarchy = new_hierarchy
        
        # 创建新章节
        section_data = HTMLSection(numbers, len(numbers), title, element, [text] if text else [])        
        self.current_section_hierarchy.append(section_data)
        return section_data

    def _parse_div_with_complex_paragraphs(self, div_element: ET.Element) -> List[HTMLSection]:
        """
        Parse a div element that may contain multiple sections within paragraphs.
        Handles cases where section titles appear in <p> or <head> elements.
        
        Args:
            div_elem: The div XML element
            parent: Parent Section object
            
        Returns:
            List of Section objects
        """
        sections = []       
        # 文本标题有几种表示形式：
        # 1. <p>1. Introduction. 正文
        # 2. <head n='2.1'>标题</head>
        # 3. <head>3.2.</head><p>标题。正文
        # 一个<div>有可能有多个section；带<head>的不一定是section。
        current_section = None
        has_section_index = (not self.current_section_hierarchy or self.current_section_hierarchy[-1].level >= 0)
        
        for child in div_element:
            if child.tag == f"{{{self.NS['tei']}}}head":
                text = self._extract_text_from_element(child)
                n_attr = child.get('n')
                numbers, title = self._parse_section_title_from_p(text, 'head', n_attr)
                if has_section_index and numbers:
                    current_section = self._update_section_hierarchy(numbers, title, child)
                    sections.append(current_section)
                else:
                    # 检查是否为全文都没有段落标号的情况。
                    # all(not text.lower().startswith(x) for x in self.NON_SECTION_KEYWORDS)
                    if not self.current_section_hierarchy or not has_section_index:
                        # 此时所有section视为同级。
                        has_section_index = False
                        current_section = HTMLSection([], -1, text, child, [])
                        self.current_section_hierarchy.append(current_section)
                        sections.append(current_section)
                    # 非章节标题的head，忽略或作为当前章节的段落处理。                    
                    elif current_section:
                        text = self._extract_text_from_element(child)
                        if text:
                            current_section.paragraphs.append(text)
            
            elif child.tag == f"{{{self.NS['tei']}}}p":
                # 首先判断是否含有标题以及标题是否合法。self._compare_section_levels(numbers)
                text = self._extract_text_from_element(child)
                numbers, title = self._parse_section_title_from_p(text, 'p') if has_section_index else (None, None)
                if numbers:
                    # 情形1
                    title, text = title
                    current_section = self._update_section_hierarchy(numbers, title, child, text)
                    sections.append(current_section)
                else:
                    # 普通段
                    if current_section and has_section_index and not current_section.title and '.' in text:
                        # 情形3
                        current_section.title, text = text.split(".", 1)
                        text = text.lstrip()
                    if text:
                        # 如果有当前章节，添加到当前章节
                        if current_section:
                            current_section.paragraphs.append(text)
                        elif self.current_section_hierarchy:
                            self.current_section_hierarchy[-1].paragraphs.append(text)
                        else:
                            # 创建第一个章节
                            title, section_content = text.split(".", 1)
                            default_section = HTMLSection([1], 1, title, None, [section_content])
                            self.current_section_hierarchy.append(default_section)
                            sections.append(default_section)
                            current_section = default_section
                
            else:
                # 视为普通段落
                text = self._extract_text_from_element(child)
                if current_section:                    
                    current_section.paragraphs.append(text)
                elif self.current_section_hierarchy:
                    self.current_section_hierarchy[-1].paragraphs.append(text)

        return sections
    
    def _fallback_parse_paragraphs(self, paper: Paper, body: ET.Element):
        """
        有些文章没有章节号不能判断章节从属关系，会导致正常的判断流程出错。
        该函数为应急方案，假如章节序号出现错乱，则去掉章节号，将所有内容视为自然段。
        """        
        for div_element in body.findall('./tei:div', self.NS):
            text_buffer = ""
            for child in div_element:
                text = self._extract_text_from_element(child)
                if child.tag.endswith("head"):
                    n_attr = child.get("n")
                    if n_attr: text = f"{n_attr} {text}"
                    text_buffer += text
                else:
                    text = f"{text_buffer} {text}"
                    paper.add_paragraph(Paragraph(father=paper, text=text))
                    text_buffer = ""                    

            if text_buffer:
                paper.add_paragraph(Paragraph(father=paper, text=text_buffer))  


# Example usage
if __name__ == "__main__":
    from utils import skeleton_to_list
    parser = XMLPaperParser()
    with open("2105.07221v2.xml", encoding='utf-8') as f:
        paper = f.read()
    paper = parser.parse(paper)
    print(len(paper.children))
    print("=" * 50 + "Skeletion" + "=" * 50)
    x, p = skeleton_to_list(paper.get_skeleton())
    print(len(p), x)
