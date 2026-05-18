import os
import sys


def _infer_jetson_model_name():
    """Try to infer a Jetson.GPIO model name from device-tree model text."""
    model_paths = ['/proc/device-tree/model', '/sys/firmware/devicetree/base/model']
    for path in model_paths:
        try:
            with open(path, 'rb') as f:
                model_text = f.read().replace(b'\x00', b' ').decode('utf-8', 'ignore').strip()
        except Exception:
            continue

        lower_text = model_text.lower()
        if 'orin nx' in lower_text:
            return 'JETSON_ORIN_NX'
        if 'orin nano' in lower_text:
            return 'JETSON_ORIN_NANO'
        if 'orin' in lower_text:
            return 'JETSON_ORIN'
        if 'xavier nx' in lower_text:
            return 'JETSON_XAVIER'
        if 'nano' in lower_text:
            return 'JETSON_NANO'
    return None

def import_board_module():
    """
    自动切换导入 Board 或 test_board，并返回 (Board模块, 是否为debug环境)
    """
    try:
        current_file_path = os.path.abspath(__file__)
        current_folder_path = os.path.dirname(current_file_path) #conf_pkg
        parent_folder_path = os.path.dirname(current_folder_path) #hexapod7
        grandparent_folder_path = os.path.dirname(parent_folder_path) #HiwonderSDK
        sys.path.append(grandparent_folder_path)
        import Board  # 实际用到的包
        is_debug_mode = False
        return Board, is_debug_mode
    except Exception as e:
        if 'Could not determine Jetson model' in str(e):
            inferred_model = _infer_jetson_model_name()
            if inferred_model is not None:
                os.environ['JETSON_MODEL_NAME'] = inferred_model
                try:
                    import Board  # 重试一次，使用推断出的模型名
                    is_debug_mode = False
                    return Board, is_debug_mode
                except Exception as retry_error:
                    e = retry_error
        print(f"[警告] 导入 Board 失败，回退到 test_board：{type(e).__name__}: {e}")
        from conf_pkg import test_board as Board  # 测试环境
        is_debug_mode = True
        return Board, is_debug_mode



if __name__ == "__main__":
    Board, is_debug_mode = import_board_module()
