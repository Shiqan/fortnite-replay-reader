from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(name='fortnite-replay-reader',
      version='0.1.6',
      description='Parse fortnite .replay files',
      long_description=readme(),
      long_description_content_type='text/markdown',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.7',
      ],
      keywords='fortnite replay reader ray',
      url='http://github.com/Shiqan/fortnite-replay-reader',
      author='Shiqan',
      license='MIT',
      packages=['ray'],
      install_requires=[
          'bitstring',
      ],
      tests_require=['pytest'],
      include_package_data=True,
      zip_safe=False)
