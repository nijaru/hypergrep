from python import Python, PythonObject
from collections import List

struct Reranker:
    var _tokenizer: PythonObject
    var _session: PythonObject
    var _initialized: Bool

    fn __init__(out self) raises:
        self._initialized = False
        self._tokenizer = PythonObject(None)
        self._session = PythonObject(None)
        
        try:
            var sys = Python.import_module("sys")
            var os = Python.import_module("os")
            
            if "src/inference" not in String(sys.path):
                sys.path.append("src/inference")            
            var current_dir = String(os.getcwd())
            var pixi_site_packages = current_dir + "/.pixi/envs/default/lib/python3.11/site-packages"
            
            if os.path.exists(pixi_site_packages):
                sys.path.append(pixi_site_packages)
            
            var ort = Python.import_module("onnxruntime")
            var tok_mod = Python.import_module("tokenizer_wrapper")
            
            var model_path = "models/reranker.onnx"
            var tokenizer_path = "models/tokenizer.json"
            
            self._tokenizer = tok_mod.RerankTokenizer(tokenizer_path)
            self._session = ort.InferenceSession(model_path)
            self._initialized = True
        except e:
            print("Failed to initialize Brain: " + String(e))

    fn rerank(self, query: String, candidates: List[String]) raises -> List[Int]:
        if not self._initialized or len(candidates) == 0:
            var indices = List[Int]()
            for i in range(len(candidates)):
                indices.append(i)
            return indices^

        var py_candidates = Python.evaluate("[]")
        for i in range(len(candidates)):
            _ = py_candidates.append(candidates[i])
            
        var inputs_tuple = self._tokenizer.prepare_inputs(query, py_candidates)
        
        var feed_dict = Python.evaluate("{}")
        var input_names = self._get_input_names()
        
        if len(input_names) >= 1:
            feed_dict[input_names[0]] = inputs_tuple[0]
        if len(input_names) >= 2:
            feed_dict[input_names[1]] = inputs_tuple[1]
        if len(input_names) >= 3:
            feed_dict[input_names[2]] = inputs_tuple[2]
            
        var res = self._session.run(PythonObject(None), feed_dict)
        
        var logits = res[0]
        var scores = logits.flatten().tolist()
        
        return self._argsort(scores)

    fn _get_input_names(self) raises -> List[String]:
        var names = List[String]()
        var inputs = self._session.get_inputs()
        var length = Int(len(inputs))
        for i in range(length):
            names.append(String(inputs[i].name))
        return names^

    fn _argsort(self, scores: PythonObject) raises -> List[Int]:
        var np = Python.import_module("numpy")
        var indices_py = np.argsort(scores)
        
        var result = List[Int]()
        var length = Int(len(indices_py))
        for i in range(length):
            var idx = Int(indices_py[length - 1 - i])
            result.append(idx)
            
        return result^
