# website

Source code for [ogu.nz](https://ogu.nz), a static site generator built with Python, HTML, SCSS, and JavaScript. Infrastructure managed with Terraform.

## Features

- Static site generation with Markdown support.
- Article and tag management.
- Customizable templates and styles.
- SEO-friendly with sitemaps and RSS feeds.

## Installation

1. Clone the repository:
   ```sh
   git clone https://github.com/tetsuo/website.git
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   npm install
   ```

## Usage

- Build the site:
  ```sh
  python generate.py
  ```
- Upload to S3 using the provided sync script:
  ```sh
  PUBLIC_S3_BUCKET_NAME="somebucket" \
  DOMAIN_NAME="example.com" \
  YES=1 \
  ./sync-public-bucket .
  ```

## License

MIT License. See [LICENSE](LICENSE) for details.
