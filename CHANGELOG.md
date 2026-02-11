# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.1] - 2026-02-11

### Fixed
- Urgent fix: removal of conflicts and correct implementation of PHASE 2 and PHASE 3
- Complete implementation of SEO improvements (PHASE 2 + PHASE 3) with regeneration of all pages

### Changed
- Exclusion of local editor and note folders from version control
- Exclusion of IDE files from version control

## [2.0.0] - 2026-02-05

### Added
- **Migration to Supabase**: Complete integration with Supabase for data storage
- **Google Analytics GA4**: Implementation of global GA4 tracking on all pages
- **Supabase Pagination**: Addition of pagination with safety limits for queries
- **Documentation Architecture**: New internal documentation structure in `_internal_docs/`
- **Split-Flap UI**: Visual interface inspired by retro airport panels
- **GitHub Pages via `/docs`**: Complete configuration for deploy via `/docs` folder
- **CNAME**: Custom domain configuration (matchfly.org)
- **`.nojekyll` file**: Configuration for GitHub Pages
- **Custom 404 page**: Personalized error page
- **Sitemap.xml**: Automatic sitemap generation for SEO

### Changed
- **Project Structure**: Complete reorganization of project architecture
- **Deploy Pipeline**: Migration to GitHub Actions with automatic updates
- **Templates**: Complete refactoring of Jinja2 templates
- **Mobile Design**: Complete redesign for better mobile experience

### Fixed
- Fixed pathing and forced inclusion of ANAC routes file
- Fixed global environment variables and Supabase logs
- Fixed timezone to America/Sao_Paulo in sync_data
- Hardened generator.py against float and None errors
- Converted data to String in sync_data to avoid type errors

## [1.5.0] - 2026-02-02

### Added
- **GitHub Actions**: Complete CI/CD configuration with automatic workflow
- **SEO Tags**: Implementation of optimized meta tags for SEO
- **Updated Dependencies**: Update of all project dependencies

### Changed
- Improvements in automatic deploy structure
- Optimization of page generation process

## [1.4.0] - 2026-01-31

### Added
- **Automatic Deploy**: Implementation of `publish.py` script for automatic deploy
- **Advanced Airline Inference**: Robust airline inference system
- **LATAM Fallback**: Implementation of fallback to recover numeric flights
- **CSV Debug**: Debug system to verify downloaded data in Actions

### Changed
- Removal of sensitive credentials from version control
- Repository cleanup to test CI/CD logic
- Disabled removal of old files to maintain SEO history

### Fixed
- Applied airline inference before validation to avoid discarding 0015 flights
- Fixed timezone in sync_data
- Removed ignored CSV from automatic commit
- Fixed secrets verification in workflow

## [1.3.0] - 2026-01-29

### Added
- **Final Pipeline**: Complete robust synchronization system and active deploy
- **Cloudflare Build**: Integration with Cloudflare for builds
- **Fixed Header**: UX improvement with fixed header and dates in alerts
- **CSV Download**: Connection of MatchFly to Monitor CSV via download

### Changed
- Correct ordering (LIFO) for flight processing
- New v2.0 pipeline structure
- Fixed SCL (Santiago) data
- Complete mobile redesign

### Fixed
- Fixed syntax in workflow URL
- Fixed secrets verification via Bash
- Fixed ordering and Cloudflare Build activation

## [1.2.0] - 2026-01-22

### Added
- **Technical Documentation**: Addition of complete technical architecture overview
- **Optimized Workflow**: Workflow modification to upload only public folder to Pages

### Changed
- Refinement of scraper logic and site generation
- Project structure improvements
- Conflict resolution maintaining local design

### Fixed
- Fixed conflicts forcing local version (clean structure + new UI)
- Project structure cleanup and UI card refinement

## [1.1.0] - 2026-01-21

### Added
- **Explicit Mapping**: Explicit mapping for Numero_Voo and separator detection
- **Data Processing**: Data normalization system and step processing

### Changed
- Refactoring of CSV to JSON conversion process
- Dependency updates
- Logging and flight data handling improvements

### Fixed
- Fixed CSV synchronization via download
- Fixed flight filtering
- Fixed CSV data update

## [1.0.0] - 2026-01-20

### Added
- **CSV Synchronization**: Data synchronization system via download
- **Playwright**: Addition of Playwright to requirements
- **Dependency Versioning**: Version specification in dependencies

### Changed
- Updated requests version in requirements.txt
- Refactored update-flights workflow for clarity
- Workflow log improvements

## [0.9.0] - 2026-01-16

### Added
- **Dependency Optimization**: Removal of unnecessary pandas/jinja
- **Bot Permissions**: Permission for bot to commit index.html updates

### Changed
- Refinement of scraper logic and site generation
- Simplified git commit pattern to root CSV only
- Explicit tracking of root CSV file in workflow

### Fixed
- Created download directories (project and system)
- Forced Downloads folder creation
- Robust directory handling for CI/CD environment

## [0.8.0] - 2026-01-15

### Added
- **Operational Monitor**: Activation of operational monitor with 15-minute frequency
- **Final Pipeline**: Transfer of Pandas logic to final build script

### Changed
- Forced file upload for trigger
- Pipeline structure improvements

## [0.1.0] - 2026-01-15

### Added
- **Initial Commit**: Creation of Open Source Flight Monitor project
- **Base Structure**: Initial MatchFly project structure
- **Flight Scraper**: Initial scraping system for Guarulhos Airport (GRU) flights
- **Page Generation**: Basic static page generation system
- **Templates**: Initial templates using Jinja2
- **Database**: JSON storage system (`data/flights-db.json`)

---

## Legend

- **Added**: for new features
- **Changed**: for changes in existing functionality
- **Deprecated**: for soon-to-be removed features
- **Removed**: for removed features
- **Fixed**: for bug fixes
- **Security**: for security vulnerabilities

[2.0.1]: https://github.com/jonechelon/matchfly-pseo/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/jonechelon/matchfly-pseo/compare/v1.5.0...v2.0.0
[1.5.0]: https://github.com/jonechelon/matchfly-pseo/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/jonechelon/matchfly-pseo/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/jonechelon/matchfly-pseo/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/jonechelon/matchfly-pseo/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/jonechelon/matchfly-pseo/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/jonechelon/matchfly-pseo/compare/v0.9.0...v1.0.0
[0.9.0]: https://github.com/jonechelon/matchfly-pseo/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/jonechelon/matchfly-pseo/compare/v0.1.0...v0.8.0
[0.1.0]: https://github.com/jonechelon/matchfly-pseo/releases/tag/v0.1.0
