#!/usr/bin/env python3

import argparse, glob, os, platform, shutil, subprocess, stat, sys, urllib.request

def run_command(command):
	if platform.system() != 'Windows' and os.sep in command[0] and not os.path.isfile(command[0]):
		sys.exit('error: failed to locate {}'.format(os.path.basename(command[0])))

	if subprocess.call(command) != 0:
		sys.exit('error: failed to execute "{}"'.format(' '.join(command)))

def escape_windows_executable_path(executable_path):
	if ' ' not in executable_path:
		return executable_path

	segments = executable_path.split('\\')
	escaped_segments = []

	for segment in segments:
		if ' ' in segment:
			segment = '"{}"'.format(segment)

		escaped_segments.append(segment)

	return '\\'.join(escaped_segments)

def make_path(root, directories):
	if not os.path.exists(root):
		os.mkdir(root)

	for directory in directories:
		root = os.path.join(root, directory)

		if not os.path.exists(root):
			os.mkdir(root)

def get_executable(name, url=None, tools_path=None, is_optional=False):
	exectable_path = None

	if tools_path != None:
		exectable_path = os.path.join(tools_path, name)

		if os.path.isfile(exectable_path):
			return exectable_path

	for directory in os.getenv('PATH', '').split(os.pathsep):
		possible_exectable_path = os.path.join(directory, name)

		if os.path.isfile(possible_exectable_path) and os.access(possible_exectable_path, os.X_OK):
			return possible_exectable_path

	if tools_path != None and url != None:
		print('info: downloading {} from {}'.format(name, url))

		urllib.request.urlretrieve(url, exectable_path)
		os.chmod(exectable_path, os.stat(exectable_path).st_mode | stat.S_IEXEC)

	if not is_optional and exectable_path == None:
		sys.exit('error: failed to locate {}'.format(name))

	return exectable_path

def deploy_locale(source_path, target_path):
	target_locale_path = os.path.join(target_path, 'locale')

	os.mkdir(target_locale_path)

	for file in glob.glob(os.path.join(source_path, 'resources', 'translations', '*.qm')):
		shutil.copy(file, target_locale_path)

def deploy_linux(qt_path, source_path, build_path, target_path, extra_libs, disable_tools_download):
	tools_path = None

	if not disable_tools_download:
		tools_path = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'appimage-tools')

		if not os.path.isdir(tools_path):
			os.mkdir(tools_path)

	appdir_deploy_command = get_executable('linuxdeploy-x86_64.AppImage', 'https://bintray.com/qtproject/linuxdeploy-mirror/download_file?file_path=2020-06-03%2Flinuxdeploy-x86_64.AppImage', tools_path)
	appimage_tool_command = get_executable('appimagetool-x86_64.AppImage', 'https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage', tools_path)

	get_executable('linuxdeploy-plugin-qt-x86_64.AppImage', 'https://bintray.com/qtproject/linuxdeploy-mirror/download_file?file_path=2020-06-03%2Flinuxdeploy-plugin-qt-x86_64.AppImage', tools_path)

	appimage_path = os.path.join(target_path, 'otter-browser')

	make_path(appimage_path, ['usr', 'share', 'applications'])
	make_path(appimage_path, ['usr', 'share', 'icons', 'hicolor'])
	make_path(appimage_path, ['usr', 'share', 'otter-browser'])
	shutil.copy(os.path.join(source_path, 'otter-browser.desktop'), os.path.join(appimage_path, 'usr/share/applications/otter-browser.desktop'))

	icons_path = os.path.join(appimage_path, 'usr/share/icons/hicolor')
	icons = [16, 32, 48, 64, 128, 256, 'scalable']

	for size in icons:
		is_raster = isinstance(size, int)
		icon_directory = '{}x{}'.format(size, size) if is_raster else size

		make_path(icons_path, [icon_directory, 'apps'])
		shutil.copy(os.path.join(source_path, 'resources/icons', 'otter-browser-{}.png'.format(size) if is_raster else 'otter-browser.svg'), os.path.join(icons_path, icon_directory, 'apps', 'otter-browser.png' if is_raster else 'otter-browser.svg'))

	deploy_locale(source_path, os.path.join(appimage_path, 'usr/share/otter-browser'))
	os.putenv('LD_LIBRARY_PATH', '{}:{}'.format(os.path.join(qt_path, 'lib'), os.getenv('LD_LIBRARY_PATH')))
	os.putenv('QMAKE', os.path.join(qt_path, 'bin/qmake'))
	run_command([appdir_deploy_command, '--plugin=qt', '--executable={}'.format(os.path.join(build_path, 'otter-browser')), '--appdir={}'.format(appimage_path)])
	shutil.rmtree(os.path.join(appimage_path, 'usr/share/doc/'), ignore_errors=True)

	libs_path = os.path.join(appimage_path, 'usr/lib')
	redundant_libs = ['libgst*-1.0.*', 'libFLAC.*', 'libogg.*', 'libvorbis*.*', 'libmount.*', 'libpulse*.*', 'libsystemd.*', 'libxml2.*']

	for pattern in redundant_libs:
		for file in glob.glob(os.path.join(libs_path, pattern)):
			os.unlink(file)

	for file in glob.glob(os.path.join(libs_path, 'libicu*.*')):
		if not os.path.exists(os.path.join(qt_path, 'lib', os.path.basename(file))):
			os.unlink(file)

	run_command([appimage_tool_command, appimage_path, os.path.join(target_path, 'otter-browser-x86_64.AppImage')])
	shutil.rmtree(appimage_path)

def deploy_windows(qt_path, source_path, build_path, target_path, extra_libs):
	seven_z_command = r'C:\Program Files\7-Zip\7z.exe'
	inno_setup_command = r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'

	if not os.path.isfile(seven_z_command):
		seven_z_command = get_executable('7z.exe', is_optional=True)

	if not os.path.isfile(inno_setup_command):
		inno_setup_command = get_executable('ISCC.exe')

	target_installer_path = os.path.join(target_path, 'input')

	os.mkdir(target_installer_path)
	shutil.copy(os.path.join(build_path, 'otter-browser.exe'), target_installer_path)
	shutil.copy(os.path.join(source_path, 'COPYING'), target_installer_path)
	deploy_locale(source_path, os.path.join(target_path, 'input'))
	run_command([escape_windows_executable_path(os.path.join(qt_path, r'bin\windeployqt.exe')), os.path.join(target_path, r'input\otter-browser.exe')])

	dlls_path = os.path.join(qt_path, 'bin')
	extra_dlls = ['libxml2*.dll', 'libxslt*.dll']

	for pattern in extra_dlls:
		for file in glob.glob(os.path.join(dlls_path, pattern)):
			shutil.copy(file, target_installer_path)

	for pattern in extra_libs:
		matches = glob.glob(pattern)

		if len(matches) == 0:
			sys.exit('error: failed to locate {}'.format(pattern))

		for file in matches:
			shutil.copy(file, target_installer_path)

	redundant_plugins = ['playlistformats', 'position', 'qmltooling', 'scenegraph', 'sensorgestures', 'sensors']

	for directory in redundant_plugins:
		shutil.rmtree(os.path.join(target_installer_path, directory), ignore_errors=True)

	inno_setup_arguments = '/DOtterWorkingDir="{}"'.format(target_path)

	if '_64' in qt_path[-5:]:
		inno_setup_arguments += ' /DOtterWin64=1'

	os.system('{} {} "{}"'.format(escape_windows_executable_path(inno_setup_command), inno_setup_arguments, os.path.join(source_path, r'packaging\otter-browser.iss')))

	release_name = 'otter-browser'

	for file in glob.glob(os.path.join(target_path, '*.exe')):
		release_name = os.path.splitext(os.path.basename(file))[0].replace('-setup', '')

		break

	target_release_path = os.path.join(target_path, release_name)

	os.rename(target_installer_path, target_release_path)

	if seven_z_command != None:
		run_command([seven_z_command, 'a', '{}.7z'.format(os.path.join(target_path, release_name)), target_release_path])

	with open(os.path.join(target_release_path, 'arguments.txt'), 'w') as file:
		file.write('--portable')

	run_command(['powershell', 'Compress-Archive', '"{}"'.format(target_release_path), '"{}.zip"'.format(os.path.join(target_path, release_name))])
	shutil.rmtree(target_release_path)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Otter Browser deployment tool.')
	parser.add_argument('--build-path', help='Path to the build directory', default=os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '../build')))
	parser.add_argument('--source-path', help='Path to the source directory', default=os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..')))
	parser.add_argument('--target-path', help='Path to the output directory', default=os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '../output')))
	parser.add_argument('--qt-path', help='Path to the Qt directory', default=os.getenv('QTDIR', ''))
	parser.add_argument('--extra-libs', help='Paths to the extra libraries to include', default=[], nargs='*')
	parser.add_argument('--disable-tools-download', help='Disable download of missing deployment tools', action='store_true')

	arguments = parser.parse_args()

	if arguments.qt_path == '':
		sys.exit('error: the following arguments are required: --qt-path')

	if platform.system() == 'Linux':
		deploy_linux(arguments.qt_path, arguments.source_path, arguments.build_path, arguments.target_path, arguments.extra_libs, arguments.disable_tools_download)
	elif platform.system() == 'Windows':
		deploy_windows(arguments.qt_path, arguments.source_path, arguments.build_path, arguments.target_path, arguments.extra_libs)
