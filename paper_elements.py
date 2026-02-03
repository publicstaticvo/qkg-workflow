from __future__ import annotations
from typing import List, Optional, Union
from dataclasses import dataclass, field


@dataclass
class Paragraph:
    """Represents a paragraph with multiple sentences"""
    father: Section
    text: str


@dataclass
class Section:
    """Represents a section, subsection, subsubsection or abstract"""
    name: str
    father: Union[Section, Paper]
    paragraphs: List[Paragraph] = field(default_factory=list)
    children: List[Section] = field(default_factory=list)
    
    def add_paragraph(self, child: Paragraph):
        self.paragraphs.append(child)
    
    def add_child(self, child: Section):
        self.children.append(child)
        
    def get_skeleton(self, section_id: str):
        repr_str = [f"\nSection {section_id} {self.name}\n"] + [{"text": p.text} for p in self.paragraphs] 
        for i, s in enumerate(self.children):
            repr_str.extend(s.get_skeleton(f"{section_id}{i + 1}."))
        return repr_str


@dataclass
class Paper(Section):
    """Represents the entire academic paper"""
    link: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    abstract: Optional[Section] = None
    references: dict = field(default_factory=dict)
    has_section_index: bool = True
    
    def get_skeleton(self) -> List[Union[str, Paragraph]]:
        repr_str = [{"text": p.text} for p in self.paragraphs]  
        for i, section in enumerate(self.children):
            repr_str.extend(section.get_skeleton(f"{i + 1}."))
        return repr_str
