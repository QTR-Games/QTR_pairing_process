# Contributing to QTR Pairing Process

Thank you for your interest in contributing to the QTR Pairing Process! This document provides guidelines for contributing to the project.

## Development Setup

Please see the **[Developer Guide](docs/DEVELOPER_GUIDE.md)** for complete development environment setup instructions.

## How to Contribute

### Reporting Issues

1. **Search Existing Issues**: Check if the issue has already been reported
2. **Use Issue Templates**: Follow the provided templates for bugs and feature requests
3. **Provide Details**: Include steps to reproduce, expected behavior, and system information
4. **Add Labels**: Help categorize the issue (bug, enhancement, documentation, etc.)

### Contributing Code

1. **Fork the Repository**: Create your own fork of the project
2. **Create Feature Branch**: Use descriptive branch names (`feature/improved-sorting`, `fix/grid-alignment`)
3. **Follow Code Standards**: See [Developer Guide - Code Style](docs/DEVELOPER_GUIDE.md#code-style-and-standards)
4. **Write Tests**: Include tests for new functionality
5. **Update Documentation**: Keep documentation current with code changes
6. **Submit Pull Request**: Use the PR template and request review

### Priority Areas

Based on user feedback, we're particularly interested in contributions to:

1. **Improved Sorting Algorithms** - Enhanced tree evaluation methods
2. **Comments/Tooltips System** - Matchup annotation functionality
3. **UI Alignment Fixes** - Grid layout and visual improvements
4. **Performance Optimization** - Tree generation and UI responsiveness

## Code Review Process

1. **Automated Checks**: Ensure tests pass and code follows style guidelines
2. **Technical Review**: Maintainers review code quality, architecture, and functionality
3. **Documentation Review**: Verify documentation is complete and accurate
4. **User Impact Assessment**: Consider impact on tournament teams and workflows
5. **Approval & Merge**: Approved changes are merged by project maintainers

## Development Guidelines

### Commit Messages

Use conventional commit format:

```text
type(scope): description

feat(ui): add comments field to matchup grid
fix(db): resolve foreign key constraint error
docs(readme): update installation instructions
refactor(tree): optimize combination generation
```

### Branch Naming

- `feature/feature-name` - New features
- `fix/issue-description` - Bug fixes
- `docs/update-description` - Documentation updates
- `refactor/component-name` - Code refactoring

### Testing Requirements

- All new features must include unit tests
- Bug fixes should include regression tests
- Integration tests for workflows spanning multiple components
- Manual testing instructions for UI changes

## Project Priorities

### Current Focus Areas

1. **User Experience Improvements**
   - Fix grid alignment issues
   - Add matchup comments functionality
   - Improve sorting algorithms

2. **Code Quality**
   - Remove deprecated legacy files
   - Improve error handling consistency
   - Optimize performance bottlenecks

3. **Documentation**
   - Keep user guides current with features
   - Expand developer onboarding materials
   - Create video tutorials for complex workflows

### Future Development

See the **[Project Scope](docs/PROJECT_SCOPE.md)** for long-term roadmap and planned enhancements.

## Community Guidelines

### Communication

- Be respectful and constructive in all interactions
- Focus on the technical merits of ideas and implementations
- Help newcomers get started with clear guidance and patience
- Share knowledge and tournament experiences to improve the tool

### Tournament Context

- Remember this tool serves competitive gaming teams under pressure
- Prioritize reliability and ease of use over complex features
- Consider the workflow of tournament day usage in design decisions
- Value feedback from active tournament participants

## Recognition

Contributors will be recognized in:

- Project README credits section
- Release notes for significant contributions
- Documentation acknowledgments
- Community showcases for innovative features

## Questions?

- **Technical Questions**: Open a GitHub issue with the "question" label
- **Development Setup**: See the [Developer Guide](docs/DEVELOPER_GUIDE.md)
- **Project Direction**: Review the [Project Scope](docs/PROJECT_SCOPE.md)

## License

By contributing to this project, you agree that your contributions will be subject to the same license terms as the project (All Rights Reserved - see project files for details).

---

Thank you for helping make QTR Pairing Process the best strategic analysis tool for competitive miniature wargaming!
