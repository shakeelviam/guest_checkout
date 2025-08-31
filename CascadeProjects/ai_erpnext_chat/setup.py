from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="ai_erpnext_chat",
    version="0.0.1",
    description="Offline AI chat via llama.cpp (Gemma) for ERPNext",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Company",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
)
