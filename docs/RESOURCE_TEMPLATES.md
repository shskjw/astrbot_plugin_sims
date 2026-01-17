# 模板资源说明

- 本插件的 HTML 模板优先使用工作区根目录下的 `resources/HTML`（即原始插件提供的模板），如果不存在，则使用插件自身 `resources/html` 目录（如果有）作为回退。

- 调试指令：在 AstrBot 中使用 `渲染模板 <模板文件名>` 可以直接渲染并返回模板的 HTML（返回前 400 字以便在聊天中查看）。

- 如果你希望插件使用特定的模板文件，请将文件放置在工作区 `resources/HTML` 下，或修改 `core/common/image_utils.HTMLRenderer` 的 `template_dir` 参数指向你的自定义路径。
