// https://stackoverflow.com/questions/37744379/create-nested-drop-down-list-in-html-css-form
class Menu {
	constructor(id){
		parent = document.getElementById(id);

		this.root = new MenuEntry("root", "root", undefined, parent);

		// this.root.appendToList(document.getElementById(id));
	}

	addMenu(path, caption, action=undefined){
		var parent = this.root;
		for (var i=0; i<path.length; i++){
			var node = parent.getSubEntry(path[i]);
			if (node == undefined){
				node = new MenuEntry(path[i], path[i], undefined);
				parent.addSubEntry(node);
			}
			parent = node;
		}

		var id = caption;

		if (parent != undefined){
			var newEntry = new MenuEntry(caption, id, action)
			parent.addSubEntry(newEntry);
		}
	}

	parseTree(path){
		var p = this.root;
		for (var i=0; i<path.length; i++){
			p = p.getSubEntry(path[i]);
			if (p == undefined){
				break;
			}
		}
		return p;
	}

}


class MenuEntry {
	constructor(caption, id, action, ul=undefined){
		this.id = id;
		this.caption = caption;

		if (ul == undefined){
			ul = document.createElement("ul");
			var li = document.createElement("li");
			var a = document.createElement("a");
			a.setAttribute("href", "#");
			var t = document.createTextNode(caption);
			a.appendChild(t);
			li.appendChild(a);
			li.appendChild(ul);
			this.objListItem = li;
		} else {
			this.objListItem = ul;
		}
		
		this.objSubList = ul;
		this.subEntries = [];
	}

	getSubEntry(id){
		if (id in this.subEntries){
			return this.subEntries[id];
		} else {
			return undefined;
		}
	}

	addSubEntry(e){
		this.subEntries[e.getId()] = e;
		e.appendToList(this.objSubList);
	}

	getId(){
		return this.id;
	}

	appendToList(parent){
		parent.appendChild(this.objListItem);
	}

}


