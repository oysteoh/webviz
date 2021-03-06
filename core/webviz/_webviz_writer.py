from os import path
import os
import re
import shutil
from uuid import uuid4
from six import itervalues


class WebvizWriter(object):
    """
    Writer for an instance of ::class:`Webviz`. The writer
    is used as a contextManager

    ::

        with WebvizWriter(destination, params, template) as writer:
            if not writer.is_clean():
                writer.clean_up()
            writer.set_up()

            image_location = writer.write_image(myImage)
            page_location = writer.write_index_page(index_page)

    Write actions return the path to the location of
    the resource written relative to destination.

    :param destination: The directory to write the instance to.
    :param parameters: global parameters used to render pages
        with.
    :param template: The main template used to render pages with.
        Assumes a page can be rendered with

        ::

            template.render(page=page,
                            root_folder=relative_path_to_root,
                            **parameters)
        The root_folder is generated by the writer for each page.
        Holds the path to the root folder of the webviz instance
        relative to where the page is written.

    """
    def __init__(self, destination, parameters, template):
        self.instance = None
        self._destination = destination
        self._template = template
        self._parameters = parameters

    sub_folders = [
        'resources',
        'sub_pages',
    ]

    index_file = 'index.html'

    def __enter__(self):
        self.instance = WebvizWriter._WebvizWriter(
            self._destination,
            self._parameters,
            self._template)
        return self.instance

    def __exit__(self, *args):
        self.instance.flush()
        self.instance = None

    class _WebvizWriter(object):
        """
        The object passed by the context manager.
        """
        def __init__(self, destination,
                     parameters, template):
            self.instance = None
            self._destination = destination
            self._template = template
            self._parameters = parameters
            self._pages = []
            self._abs_folders = {
                sub_folder: path.join(self._destination, sub_folder)
                for sub_folder in WebvizWriter.sub_folders
            }
            self._index_path = path.join(self._destination,
                                         WebvizWriter.index_file)

        def flush(self):
            for (page, root_path) in self._pages:
                page_path = path.join(self._destination, page.location)
                with open(page_path, 'w') as page_handle:
                    page_handle.write(self._render_page(page, root_path))

        def _render_page(self, page, root_folder):
            """
            :returns: The given page rendered as html.
            :param page: The page to render.
            :param root_folder: The directory of the root_folder of
                the webviz instance, relative to the the
                page that is being rendered.
            """
            page.current_page = True
            html = self._template.render(dict(page=page,
                                              root_folder=root_folder,
                                              **self._parameters))
            page.current_page = False
            return html

        def write_index_page(self, page):
            """
            Write the given page as the index page of the webviz
            instance.
            """
            page.location = path.join('.', WebvizWriter.index_file)
            self._pages.append((page, '.'))
            return page.location

        def write_sub_page(self, page):
            """
            Write the given page as a sub page of the
            webviz instance.
            """

            filtered_title = re.sub('[^a-z0-9_]+', '',
                                    page.title.lower().replace(' ', '_'))
            file_name = '{}_{}.html'.format(filtered_title, len(self._pages))
            page.location = path.join('sub_pages', file_name)
            self._pages.append((page, '..'))
            return page.location

        def write_js_file(self, js_file):
            return self.write_resource(js_file,
                                       target_postfix='.js',
                                       subdir='js')

        def write_css_file(self, css_file):
            return self.write_resource(css_file,
                                       target_postfix='.css',
                                       subdir='css')

        def write_resource(self,
                           src_file,
                           target_name=None,
                           target_postfix='',
                           subdir=None):
            """
            Write a file to the 'resources' subfolder.
            :param src_file: Either location of file,
                or a file object of the resource to copy into
                to site.
            :param target_name: Resulting name of the file, defaults
                to the name of the file. If the file has no name, a
                name is randomly generated.
            :param target_postfix: If a filename is generated, the
                postfix of that file name.
            :param subdir: Optional subdir of the resource in the
                resources folder.
            :returns: the resulting path to file, relative to
                the project root.
            """
            dest = None
            if subdir:
                dest = path.join(self._abs_folders['resources'], subdir)
            else:
                dest = self._abs_folders['resources']

            if not os.path.exists(dest):
                os.makedirs(dest)

            if isinstance(src_file, str):
                target_name = path.basename(src_file)
                shutil.copy(src_file, dest)
            else:
                try:
                    target_name = path.basename(src_file.name)
                except AttributeError:
                    target_name = str(uuid4()) + target_postfix
                with open(path.join(dest, target_name), 'w') as f:
                    try:
                        for line in src_file:
                            f.write(line)
                    finally:
                        src_file.close()
            relative = None
            if subdir:
                relative = path.join('resources', subdir)
            else:
                relative = 'resources'
            return path.join(relative, target_name)

        def set_up(self):
            """
            Sets up the folder structure of the webviz instance
            if the instance directory is clean.
            :raises: OSError, if the instance directory is not clean.
            """
            if not path.exists(self._destination):
                os.mkdir(self._destination)

            for folder in itervalues(self._abs_folders):
                    if not path.exists(folder):
                        os.mkdir(folder)

        def is_clean(self):
            """
                Looks for any of the subfolders used to store an
                instance (see WebvizWriter.sub_folders) or an index
                file. If one exists, the directory is dirty and writing might
                result in overwritten files.
                :returns: True if the instance destination is clean.
            """
            for folder in self._abs_folders.values():
                if path.exists(folder):
                    return False
            if path.exists(self._index_path):
                return False
            return True

        def clean_up(self):
            """
            Cleans up the instance directory.
            """
            for folder in self._abs_folders.values():
                if path.exists(folder):
                    shutil.rmtree(folder)
            if path.exists(self._index_path):
                os.remove(self._index_path)
