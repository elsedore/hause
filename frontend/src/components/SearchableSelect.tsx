import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

export interface SelectOption {
  value: string;
  label: string;
}

interface SearchableSelectProps {
  label: string;
  options: SelectOption[];
  value: string;
  placeholder: string;
  disabled?: boolean;
  required?: boolean;
  onChange: (value: string) => void;
}

export function SearchableSelect({
  label,
  options,
  value,
  placeholder,
  disabled = false,
  required = false,
  onChange,
}: SearchableSelectProps) {
  const listId = useId();
  const root = useRef<HTMLDivElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const selected = options.find((option) => option.value === value);
  const filteredOptions = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("fr");
    if (!normalizedQuery) return options;
    return options.filter((option) =>
      option.label.toLocaleLowerCase("fr").includes(normalizedQuery),
    );
  }, [options, query]);
  const visibleOptions = filteredOptions.slice(0, 100);

  useEffect(() => {
    function closeOnOutsideClick(event: PointerEvent) {
      if (!root.current?.contains(event.target as Node)) setIsOpen(false);
    }
    document.addEventListener("pointerdown", closeOnOutsideClick);
    return () => document.removeEventListener("pointerdown", closeOnOutsideClick);
  }, []);

  function choose(option: SelectOption) {
    onChange(option.value);
    setQuery("");
    setIsOpen(false);
    setActiveIndex(0);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setIsOpen(true);
      setActiveIndex((index) =>
        filteredOptions.length ? (index + 1) % filteredOptions.length : 0,
      );
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setIsOpen(true);
      setActiveIndex((index) =>
        filteredOptions.length
          ? (index - 1 + filteredOptions.length) % filteredOptions.length
          : 0,
      );
    } else if (event.key === "Enter" && isOpen && filteredOptions[activeIndex]) {
      event.preventDefault();
      choose(filteredOptions[activeIndex]);
    } else if (event.key === "Escape") {
      setIsOpen(false);
      setQuery("");
    }
  }

  return (
    <div className="searchable-select" ref={root}>
      <input
        type="text"
        role="combobox"
        aria-label={label}
        aria-autocomplete="list"
        aria-expanded={isOpen}
        aria-controls={listId}
        aria-activedescendant={
          isOpen && visibleOptions[activeIndex]
            ? `${listId}-option-${activeIndex}`
            : undefined
        }
        autoComplete="off"
        required={required}
        disabled={disabled}
        placeholder={placeholder}
        value={isOpen ? query : selected?.label ?? ""}
        onFocus={() => {
          setQuery("");
          setIsOpen(true);
          setActiveIndex(0);
        }}
      onChange={(event) => {
          setQuery(event.target.value);
          setActiveIndex(0);
          setIsOpen(true);
          onChange("");
        }}
      onKeyDown={handleKeyDown}
      onClick={() => setIsOpen(true)}
      />
      <span className="searchable-select-arrow" aria-hidden="true">⌄</span>
      {isOpen && !disabled && (
        <ul className="searchable-select-options" id={listId} role="listbox">
          {visibleOptions.length ? (
            visibleOptions.map((option, index) => (
              <li
                id={`${listId}-option-${index}`}
                key={option.value}
                role="option"
                aria-selected={option.value === value}
                className={index === activeIndex ? "active" : ""}
                onMouseEnter={() => setActiveIndex(index)}
                onMouseDown={(event) => event.preventDefault()}
                onClick={(event) => {
                  // The control sits inside a label; prevent its default click
                  // from refocusing the input and reopening the list.
                  event.preventDefault();
                  event.stopPropagation();
                  choose(option);
                }}
              >
                {option.label}
              </li>
            ))
          ) : (
            <li className="no-options" role="presentation">
              Aucun résultat. Modifiez votre recherche.
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
