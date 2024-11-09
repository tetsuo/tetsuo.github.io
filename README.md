# website

This repository contains the source code for [ogu.nz](https://ogu.nz). The site includes articles, resources, and updates. It is built using a combination of HTML, SCSS, Python, and JavaScript, with infrastructure management using Terraform.

## Features

- **Static Site Generation**: Generates a static website with custom templates.
- **Article Management**: Contains a collection of articles stored in the `articles` directory.
- **Infrastructure as Code**: Uses Terraform to manage infrastructure resources for deployment.

## Installation

1. Clone the repository:
   ```sh
   git clone https://github.com/onur1/website.git
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   npm install
   ```

## Usage

- **Generate Content**: Use `generate.py` to build the site.
- **Deploy**: The `sync-public-bucket` script can be used to sync files to a public hosting bucket.

## License

MIT License. See [LICENSE](LICENSE) for details.
