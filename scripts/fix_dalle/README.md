# DALL-E Image Fix Scripts

These scripts fix the issue with DALL-E generated images in the carchive database. The problem is that while DALL-E images (.webp files) are physically present in the database, they are:

1. Not marked as AI-generated (`is_generated = false`)
2. Not properly associated with their tool/assistant messages
3. Not using the correct `association_type` ('generated' vs 'attachment')

## Scripts Overview

This directory contains three scripts:

1. **find_dalle_images.py** - Identifies DALL-E images (.webp files) and marks them as AI-generated
2. **update_media_paths.py** - Ensures file paths in the media table point to the correct locations
3. **associate_images.py** - Creates proper associations between DALL-E images and their messages

## How to Use

You can run all scripts at once using the bash script:

```bash
bash scripts/fix_dalle/fix_dalle_media.sh
```

Or run each script individually:

```bash
# Step 1: Identify and mark DALL-E images
python scripts/fix_dalle/find_dalle_images.py

# Step 2: Fix file paths
python scripts/fix_dalle/update_media_paths.py

# Step 3: Create message associations
python scripts/fix_dalle/associate_images.py
```

## Technical Details

### How the Scripts Work

1. **Finding DALL-E Images**:
   - Scans the `chat2/dalle-generations` directory for .webp files
   - Extracts file IDs from the filenames using regex
   - Updates corresponding media records to set `is_generated = true`

2. **Updating Media Paths**:
   - Ensures DALL-E images in `media/chatgpt` have correct paths in the database
   - Copies missing files from `chat2/dalle-generations` to `media/chatgpt` if needed
   - Updates media records to point to the correct locations

3. **Associating Images with Messages**:
   - Finds tool messages containing "DALL-E" references
   - Extracts file IDs from the message content
   - Links the images to both the tool message and the following assistant message
   - Sets the `association_type` to 'generated'

### Database Model Relationships

- **Media**: Stores information about the media file itself
  - `is_generated`: Flag indicating if the image was AI-generated
  - `file_path`: Path to the physical file
  - `original_file_id`: Original file ID from the ChatGPT export

- **MessageMedia**: Junction table linking messages to media
  - `message_id`: The message associated with the media
  - `media_id`: The media file
  - `association_type`: 'attachment', 'inline', or 'generated'

## Results

After running these scripts:

1. All DALL-E generated images will be properly marked as `is_generated = true`
2. The images will be correctly linked to their corresponding tool and assistant messages
3. The `association_type` will be set to 'generated'
4. Conversations rendered through the carchive system will display the generated images