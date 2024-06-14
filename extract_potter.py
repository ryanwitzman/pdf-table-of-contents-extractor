import requests
import json

def get_sections(file_path):
    # Define the API endpoint
    url = "http://localhost:5070"
    
    # Make the request to the API
    with open(file_path, 'rb') as f:
        response = requests.post(url, files={"file": f})
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Failed to get response from API. Status code: {response.status_code}")
        return None
    
    # Parse the response JSON
    data = response.json()
    return data

# Use the function to get sections from the given PDF file
file_path = "2303.18223v13 (1).pdf"
sections = get_sections(file_path)

def organize_sections(sections):
    organized_sections = {}
    section_stack = []  # Stack to keep track of the current nesting of sections
    
    for section in sections:
        label = section['label']
        start_page = section['selectionRectangles'][0]['page']
        end_page = section['selectionRectangles'][-1]['page']
        indentation = section['indentation']
        
        # Create a new section dictionary
        new_section = {
            'start_page': start_page,
            'end_page': end_page,
            'subsections': {}
        }
        
        if not section_stack:
            # If stack is empty, it's a top-level section
            organized_sections[label] = new_section
            section_stack.append((indentation, new_section))
        else:
            # Pop the stack until the current section's parent is found
            while section_stack and section_stack[-1][0] >= indentation:
                section_stack.pop()
            
            if section_stack:
                # Add the new section as a subsection of the last section in the stack
                last_section = section_stack[-1][1]
                last_section['subsections'][label] = new_section
            else:
                # If the stack is empty after popping, this is a top-level section
                organized_sections[label] = new_section
                
            # Update the end page of all parent sections, if necessary
            for _, sec in section_stack:
                if sec['end_page'] < end_page:
                    sec['end_page'] = end_page
            
            # Push the new section onto the stack
            section_stack.append((indentation, new_section))
    
    return organized_sections

# Usage example with the sections data

# Organize the input data
organized_sections = organize_sections(sections)

# Print the organized sections
print(json.dumps(organized_sections, indent=2))
