"""
Fastie Template Engine - Mako wrapper for code generation
"""

from mako.template import Template
from mako.lookup import TemplateLookup
from mako.exceptions import RichTraceback, TemplateLookupException
from pathlib import Path
from typing import Dict, Any
import click
import tempfile
import os


from fastie.core.decorators.di import component

@component(lazy=False)
class FastieTemplateEngine:
    """Template engine wrapper for Fastie CLI using Mako templates"""
    
    def __init__(self):
        """Initialize the template engine with proper lookup directories"""
        self.templates_dir = Path(__file__).parent / 'templates'
        
        # Create temp directory for Mako modules that works on all platforms
        self.module_dir = Path(tempfile.gettempdir()) / 'mako_modules'
        self.module_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure templates directory exists
        if not self.templates_dir.exists():
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            
        self.lookup = TemplateLookup(
            directories=[str(self.templates_dir)],
            module_directory=str(self.module_dir),
            strict_undefined=True,
            input_encoding='utf-8',
            output_encoding=None,  # Return Unicode strings, not bytes
            preprocessor=[self._clean_whitespace]  # Pre-process template content
        )
    
    def render(self, template_name: str, **context) -> str:
        """
        Render a template with given context
        
        Args:
            template_name: Path to template file relative to templates directory
            **context: Template variables
            
        Returns:
            Rendered template content
        """
        try:
            # Verify template exists
            if not self.template_exists(template_name):
                raise FileNotFoundError(f"Template not found: {template_name}")
            
            template = self.lookup.get_template(template_name)
            rendered = template.render(**context)
            
            # Post-process to clean up extra blank lines
            return self._clean_output(rendered)
            
        except FileNotFoundError as e:
            click.echo(f"❌ Template error: {str(e)}")
            click.echo(f"💡 Available templates in {os.path.dirname(template_name)}:")
            templates = self.list_templates(os.path.dirname(template_name))
            for t in templates:
                click.echo(f"   - {t}")
            raise
        except Exception as e:
            self._handle_template_error(template_name, e)
            raise
    
    def _clean_whitespace(self, text):
        """Pre-process template to handle whitespace"""
        # Remove trailing whitespace from lines
        lines = text.split('\n')
        lines = [line.rstrip() for line in lines]
        return '\n'.join(lines)
    
    def _clean_output(self, text: str) -> str:
        """Clean up rendered template output"""
        lines = text.split('\n')
        cleaned_lines = []
        prev_line_empty = False
        
        for line in lines:
            line = line.rstrip()  # Remove trailing whitespace
            
            # Handle lines with content
            if line.strip():
                cleaned_lines.append(line)
                prev_line_empty = False
            # Handle empty lines - keep only one
            elif not prev_line_empty and cleaned_lines:
                cleaned_lines.append('')
                prev_line_empty = True
        
        # Ensure single trailing newline
        return '\n'.join(cleaned_lines).rstrip() + '\n'
    
    def _handle_template_error(self, template_name: str, error: Exception):
        """Handle template rendering errors with helpful debugging info"""
        click.echo(f"❌ Template error in {template_name}:")
        
        if isinstance(error, TemplateLookupException):
            click.echo(f"   Template not found: {template_name}")
            click.echo(f"   Available templates:")
            for t in self.list_templates(os.path.dirname(template_name)):
                click.echo(f"   - {t}")
        else:
            click.echo(f"   {str(error)}")
            
            # Show Mako traceback if available
            if hasattr(error, 'source') or 'mako' in str(error).lower():
                try:
                    traceback = RichTraceback()
                    for (filename, lineno, function, line) in traceback.traceback:
                        click.echo(f"   File {filename}, line {lineno}, in {function}")
                        if line:
                            click.echo(f"     {line}")
                    click.echo(f"   {traceback.error}")
                except:
                    pass  # Fallback to basic error message
    
    def template_exists(self, template_name: str) -> bool:
        """Check if a template file exists"""
        template_path = self.templates_dir / template_name
        return template_path.exists() and template_path.is_file()
    
    def list_templates(self, directory: str = None) -> list:
        """List available templates in a directory"""
        search_dir = self.templates_dir
        if directory:
            search_dir = search_dir / directory
            
        if not search_dir.exists():
            return []
            
        templates = []
        for f in search_dir.glob('*.mako'):
            if f.is_file():
                templates.append(f.name)
        return sorted(templates)


# Global template engine instance
template_engine = FastieTemplateEngine()


def render_template(template_name: str, **context) -> str:
    """Convenience function to render templates"""
    return template_engine.render(template_name, **context)


def get_template_helpers():
    """Common template helper functions"""
    return {
        'to_class_name': lambda name: ''.join(word.capitalize() for word in name.lower().replace('-', '_').split('_')),
        'to_snake_case': lambda name: name.lower().replace('-', '_'),
        'to_title_case': lambda name: name.replace('_', ' ').replace('-', ' ').title(),
        'to_plural': lambda name: f"{name}s" if not name.endswith('s') else name,
        'to_table_name': lambda name: f"{name.lower().replace('-', '_')}s"
    } 