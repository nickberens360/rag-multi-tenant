# Auto-Discovery System for RAG Data Sources

The auto-discovery system makes it incredibly easy to add new JSON data sources to your RAG system with minimal or zero configuration required.

## Overview

Instead of manually configuring every data source in `data_sources.yaml`, you can now:

1. **Drop a JSON file** in the `public/` directory
2. **Run with auto-discovery** enabled
3. **Get automatic configuration** including templates, retrievers, and metadata

The system intelligently analyzes JSON structure and generates appropriate configurations based on common patterns.

## Quick Start

### Adding a New Data Source (Zero Configuration)

1. **Add your JSON file** to the `public/` directory:
```bash
# Copy your JSON file to the public directory
cp my_data.json public/
```

2. **Build with auto-discovery**:
```bash
python3 backend/scripts/build_unified_data.py --auto-discover
```

That's it! Your data source is now available in the RAG system.

### Using the CLI Tool

The CLI tool provides easy commands for managing data sources:

```bash
# List all sources (manual + auto-discoverable)
python3 -m backend.tools.datasource list --details

# Add a new source with auto-configuration
python3 -m backend.tools.datasource add my_data.json

# Generate YAML configuration for manual editing
python3 -m backend.tools.datasource generate my_data > config.yaml
```

## Supported JSON Structures

The auto-discovery system supports three main JSON structures:

### 1. List-Based Sources (Array at Root)

**Example: `projects.json`**
```json
[
  {
    "title": "My Project",
    "description": "A cool project",
    "technologies": ["React", "Node.js"],
    "year": "2024"
  },
  {
    "title": "Another Project",
    "description": "Another cool project",
    "technologies": ["Vue.js", "Python"],
    "year": "2023"
  }
]
```

**Auto-Generated Configuration:**
- **Type**: List source (`is_list_source: true`)
- **Fields**: Automatically detected from common fields
- **Template**: Prioritizes important fields like `title`, `description`
- **Metadata**: Uses identifying fields like `title` for search
- **Special Processing**: Arrays like `technologies` are joined with commas

### 2. Object-Based Sources with Sections

**Example: `experience.json`**
```json
{
  "summary": "Brief overview of experience",
  "positions": [
    {
      "company": "Tech Corp",
      "role": "Developer",
      "dates": "2022-2024",
      "responsibilities": ["Built apps", "Led team"]
    }
  ],
  "skills": ["JavaScript", "Python"]
}
```

**Auto-Generated Configuration:**
- **Type**: Object source with sections
- **Sections**: Each top-level field becomes a section
- **Templates**: Generated for each section type
- **List Handling**: Arrays are processed as list sections
- **Metadata**: Important fields like `company`, `role` are extracted

### 3. Mixed Object Sources

**Example: `portfolio.json`**
```json
{
  "bio": "Personal biography",
  "projects": [
    {"title": "Project 1", "description": "Description 1"},
    {"title": "Project 2", "description": "Description 2"}
  ],
  "contact": {
    "email": "user@example.com",
    "location": "City, State"
  }
}
```

**Auto-Generated Configuration:**
- **Flexible Processing**: Handles strings, arrays, and nested objects
- **Smart Templates**: Adapts to different field types
- **Comprehensive Coverage**: All fields are included in the configuration

## Field Priority and Template Generation

The system uses intelligent field prioritization for template generation:

### High Priority Fields (Used First in Templates)
- `title`, `name`, `heading` - Primary identifiers
- `description`, `content`, `summary` - Main content
- `company`, `role`, `institution` - Context information

### Special Processing Fields
- `tags`, `skills`, `technologies` - Joined with commas
- `points`, `responsibilities` - Formatted as bullet points
- `dates`, `year` - Temporal information

### Example Generated Template
```yaml
projects_template: |
  Title: {title}
  Description: {description}
  Year: {year}
  Technologies: {technologies}
```

## Command Reference

### Build Script Commands

```bash
# Standard build (manual sources only)
python3 backend/scripts/build_unified_data.py

# Build with auto-discovery
python3 backend/scripts/build_unified_data.py --auto-discover

# Force rebuild with auto-discovery
python3 backend/scripts/build_unified_data.py --auto-discover --force

# Watch mode with auto-discovery (for development)
python3 backend/scripts/build_unified_data.py --watch --auto-discover

# List all available sources
python3 backend/scripts/build_unified_data.py --list-sources
```

### CLI Tool Commands

```bash
# List sources
python3 -m backend.tools.datasource list
python3 -m backend.tools.datasource list --details

# Add new source
python3 -m backend.tools.datasource add path/to/file.json
python3 -m backend.tools.datasource add file.json --no-auto-configure

# Generate configuration
python3 -m backend.tools.datasource generate source_name
python3 -m backend.tools.datasource generate source_name -o config.yaml
```

## Development Workflow

### For Development (Watch Mode)

```bash
# Start watch mode with auto-discovery
python3 backend/scripts/build_unified_data.py --watch --auto-discover
```

This will:
- Watch for file changes in the `public/` directory
- Automatically rebuild when JSON files are added/modified
- Include auto-discovered sources in each rebuild
- Provide real-time feedback

### For Production

```bash
# Build with auto-discovery for production
python3 backend/scripts/build_unified_data.py --auto-discover --force
```

## Integration with Manual Configuration

The auto-discovery system works seamlessly with manual configuration:

1. **Manual sources take precedence** - If a source is manually configured, auto-discovery skips it
2. **Hybrid approach** - You can have both manual and auto-discovered sources
3. **Override capability** - Add manual configuration for any auto-discovered source to customize it

### Example Workflow

1. **Start with auto-discovery** for rapid prototyping
2. **Generate configuration** for sources that need customization:
   ```bash
   python3 -m backend.tools.datasource generate projects -o projects_config.yaml
   ```
3. **Add to manual configuration** by copying the generated YAML to `data_sources.yaml`
4. **Customize as needed** (templates, retrievers, special processing)

## Best Practices

### JSON File Structure

1. **Use descriptive field names**: `title`, `description`, `company`, `role`
2. **Be consistent**: Use the same field names across similar items
3. **Group related data**: Use arrays for lists, objects for structured data
4. **Include metadata**: Add fields like `year`, `category`, `tags` for better search

### File Naming

1. **Use descriptive names**: `projects.json`, `experience.json`, `skills.json`
2. **Avoid spaces**: Use underscores or hyphens instead
3. **Be consistent**: Follow a naming convention across your files

### Field Naming Conventions

For optimal auto-discovery results, use these field names when possible:

- **Identifiers**: `title`, `name`, `heading`
- **Content**: `description`, `content`, `summary`
- **Context**: `company`, `role`, `institution`, `degree`
- **Temporal**: `dates`, `year`, `period`
- **Categorization**: `tags`, `category`, `type`
- **Lists**: `skills`, `technologies`, `responsibilities`, `points`

## Troubleshooting

### Common Issues

1. **Source not detected**
   - Ensure the JSON file is in the `public/` directory
   - Check that the JSON is valid (use a JSON validator)
   - Verify the file has a `.json` extension

2. **Poor template generation**
   - Use standard field names (`title`, `description`, etc.)
   - Ensure consistent field names across array items
   - Check that objects have the expected structure

3. **Missing fields in templates**
   - The system prioritizes common fields
   - Generate configuration manually for full control:
     ```bash
     python3 -m backend.tools.datasource generate source_name
     ```

### Debug Commands

```bash
# Check what sources are discoverable
python3 -m backend.tools.datasource list --details

# Generate configuration to see what would be created
python3 -m backend.tools.datasource generate source_name
```

## Advanced Usage

### Custom Configuration Generation

If you need more control over the generated configuration:

1. **Generate base configuration**:
   ```bash
   python3 -m backend.tools.datasource generate projects -o projects.yaml
   ```

2. **Edit the generated YAML** to customize:
   - Templates
   - Retriever keywords
   - Special processing rules
   - Metadata fields

3. **Add to manual configuration** in `data_sources.yaml`

### Extending Auto-Discovery

The auto-discovery system is designed to be extensible. Key files:

- `backend/core/auto_discovery.py` - Main auto-discovery logic
- `backend/scripts/build_unified_data.py` - Integration with build process
- `backend/tools/datasource.py` - CLI tool for management

## Examples

### Example 1: Adding a Blog Posts Source

1. **Create `blog_posts.json`**:
```json
[
  {
    "title": "Getting Started with RAG",
    "content": "RAG systems combine retrieval and generation...",
    "tags": ["AI", "RAG", "Tutorial"],
    "date": "2024-01-15",
    "author": "Nick Berens"
  }
]
```

2. **Add with auto-discovery**:
```bash
python3 -m backend.tools.datasource add blog_posts.json
python3 backend/scripts/build_unified_data.py --auto-discover
```

3. **Result**: Automatic configuration with proper template and retriever

### Example 2: Adding a Skills Database

1. **Create `skills.json`**:
```json
{
  "frontend": [
    {"name": "React", "level": "Expert", "years": 5},
    {"name": "Vue.js", "level": "Expert", "years": 3}
  ],
  "backend": [
    {"name": "Python", "level": "Expert", "years": 7},
    {"name": "Node.js", "level": "Intermediate", "years": 2}
  ]
}
```

2. **Auto-discover and build**:
```bash
python3 backend/scripts/build_unified_data.py --auto-discover
```

3. **Result**: Sections for `frontend` and `backend` with appropriate templates

## Migration Guide

### From Manual Configuration

If you have existing manual configurations and want to use auto-discovery:

1. **Keep existing manual sources** - they will continue to work
2. **Add new sources** using auto-discovery
3. **Gradually migrate** by removing manual config and using auto-discovery
4. **Test thoroughly** to ensure no functionality is lost

### Validation

Always validate your setup after changes:

```bash
# List all sources to verify configuration
python3 -m backend.tools.datasource list --details

# Test build process
python3 backend/scripts/build_unified_data.py --auto-discover --force

# Verify unified data file
python3 -c "import json; print(list(json.load(open('public/unified_data.json')).keys()))"
```

## Conclusion

The auto-discovery system dramatically simplifies adding new data sources to your RAG system. With just a JSON file and a single command, you can have a fully configured data source with appropriate templates, retrievers, and metadata extraction.

The system is designed to be:
- **Convention over configuration** - Smart defaults for common patterns
- **Flexible** - Handles various JSON structures
- **Extensible** - Easy to customize when needed
- **Compatible** - Works alongside existing manual configuration

Start with auto-discovery for rapid development, then customize as needed for production use.