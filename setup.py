from setuptools import setup, find_packages

setup(
    name='django-nginx-filter-image',
    version='0.9',
    description='Django template tags for nginx image filter.',
    long_description=open('README.md').read(),
    author='BlackWizard',
    author_email='BlackWizard@mail.ru',
    url='http://github.com/BlackWizard/django-nginx-filter-image',
    packages=find_packages(exclude=[]),
    include_package_data=True,
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ],
    zip_safe=False,
)
